import os
import re
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from database import Database

# Load environment variables for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in production

# Initialize Slack app with Bot Token and Signing Secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize Flask app for HTTP endpoints
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# Lazy-load database to prevent startup crashes
_db = None

def get_db():
    """Get database instance (lazy initialization)"""
    global _db
    if _db is None:
        try:
            _db = Database()
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")
            print("⚠️ Bot will run but won't persist data")
    return _db


def classify_message(event):
    """Classify message as file or text"""
    has_files = "files" in event and len(event["files"]) > 0
    if has_files:
        file_types = [f.get("mimetype", "unknown") for f in event["files"]]
        return "file", file_types
    return "text", []


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


def is_spot_from_file_shared(file_id, channel_id):
    """
    Check if a file_shared event is a spot:
    - File must be an image
    - Message must tag at least one user
    """
    try:
        # Get file info
        file_info = app.client.files_info(file=file_id)
        file_data = file_info["file"]
        
        # Check if it's an image
        has_image = file_data.get("mimetype", "").startswith("image/")
        if not has_image:
            return False, []
        
        # Get the message with the file to check for mentions
        # The file shares array contains the channel and timestamp
        shares = file_data.get("shares", {})
        
        # Check public channels
        public_shares = shares.get("public", {})
        if channel_id in public_shares:
            # Get the most recent share in this channel
            share_info = public_shares[channel_id][0]  # First share
            ts = share_info.get("ts")
            
            # Fetch the actual message
            result = app.client.conversations_history(
                channel=channel_id,
                latest=ts,
                limit=1,
                inclusive=True
            )
            
            if result["messages"]:
                text = result["messages"][0].get("text", "")
                user_mentions = re.findall(r"<@([A-Z0-9]+)>", text)
                return len(user_mentions) > 0, user_mentions
        
        return False, []
    except Exception as e:
        print(f"Error checking file_shared event: {e}")
        return False, []


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
    
    # Classify the message
    msg_type, file_types = classify_message(event)
    print(f"📩 Message classified as '{msg_type}' from {sender_id}")
    if msg_type == "file":
        print(f"   File types: {', '.join(file_types)}")
    
    # Check if this is a spot
    is_valid_spot, tagged_users = is_spot(event)
    
    if is_valid_spot:
        # Process the spot
        num_tagged = len(tagged_users)
        
        # Get sender's username
        sender_username = get_username(sender_id)
        
        # Update database
        db = get_db()
        if db:
            # Sender gets +1 point per person tagged
            db.add_points(sender_id, num_tagged, sender_username)
            
            # Each tagged user loses 1 point
            for tagged_user in tagged_users:
                tagged_username = get_username(tagged_user)
                db.subtract_points(tagged_user, 1, tagged_username)
        
        print(f"✅ Spot processed: {sender_username} ({sender_id}) tagged {num_tagged} users")


@app.event("file_shared")
def handle_file_shared(event, say):
    """Handle file_shared events (alternative way Slack sends file messages)"""
    file_id = event.get("file_id")
    channel_id = event.get("channel_id")
    user_id = event.get("user_id")
    
    if not file_id or not user_id:
        return
    
    print(f"📎 File shared event detected from {user_id} in channel {channel_id}")
    
    # Check if this is a spot
    is_valid_spot, tagged_users = is_spot_from_file_shared(file_id, channel_id)
    
    if is_valid_spot:
        # Process the spot
        num_tagged = len(tagged_users)
        
        # Get sender's username
        sender_username = get_username(user_id)
        
        # Update database
        db = get_db()
        if db:
            # Sender gets +1 point per person tagged
            db.add_points(user_id, num_tagged, sender_username)
            
            # Each tagged user loses 1 point
            for tagged_user in tagged_users:
                tagged_username = get_username(tagged_user)
                db.subtract_points(tagged_user, 1, tagged_username)
        
        print(f"✅ Spot processed (file_shared): {sender_username} ({user_id}) tagged {num_tagged} users")


@flask_app.route("/", methods=["GET"])
def home():
    """Root endpoint"""
    return {"status": "running", "service": "spotted-bot", "endpoints": ["/health", "/slack/events"]}, 200


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle incoming Slack events via HTTP POST"""
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for deployment platforms"""
    status = {
        "status": "healthy",
        "service": "spotted-bot",
        "slack_configured": bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_SIGNING_SECRET")),
        "supabase_configured": bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))
    }
    
    # Test database connection
    try:
        db = get_db()
        status["database_connected"] = db is not None
    except Exception as e:
        status["database_connected"] = False
        status["database_error"] = str(e)
    
    return status, 200


def start():
    """Start the Flask web server"""
    port = int(os.environ.get("PORT", 3000))
    print(f"⚡️ Spotted Bot is running on port {port}!")
    flask_app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    start()

