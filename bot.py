import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from database import Database

# Load environment variables for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in production

# Initialize Slack app with Bot Token
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
db = Database()


def is_spot(event):
    """
    Check if a message is a 'spot':
    - Must have at least one image/file
    - Must tag at least one user
    """
    # Check for files/images
    has_image = False
    if "files" in event:
        # Check if any file is an image
        has_image = any(
            f.get("mimetype", "").startswith("image/") for f in event["files"]
        )
    
    # Check for user mentions
    text = event.get("text", "")
    user_mentions = re.findall(r"<@([A-Z0-9]+)>", text)
    
    return has_image and len(user_mentions) > 0, user_mentions


def get_username(user_id):
    """Fetch username from Slack API"""
    try:
        result = app.client.users_info(user=user_id)
        user = result["user"]
        # Prefer display_name, fall back to real_name or name
        return user.get("profile", {}).get("display_name") or user.get("real_name") or user.get("name") or user_id
    except Exception as e:
        print(f"Error fetching username for {user_id}: {e}")
        return None


@app.event("message")
def handle_message(event, say):
    """Handle all messages in channels the bot is in"""
    # Ignore bot messages and message changes
    if event.get("subtype") is not None:
        return
    
    sender_id = event.get("user")
    if not sender_id:
        return
    
    # Check if this is a spot
    is_valid_spot, tagged_users = is_spot(event)
    
    if is_valid_spot:
        # Process the spot
        num_tagged = len(tagged_users)
        
        # Get sender's username
        sender_username = get_username(sender_id)
        
        # Update database
        # Sender gets +1 point per person tagged
        db.add_points(sender_id, num_tagged, sender_username)
        
        # Each tagged user loses 1 point
        for tagged_user in tagged_users:
            tagged_username = get_username(tagged_user)
            db.subtract_points(tagged_user, 1, tagged_username)
        
        print(f"Spot processed: {sender_username} ({sender_id}) tagged {num_tagged} users")


def start():
    """Start the bot using Socket Mode"""
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Spotted Bot is running!")
    handler.start()


if __name__ == "__main__":
    start()

