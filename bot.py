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


# Track recent file shares (channel_id -> {user_id, timestamp, file_id})
# Used to match files with tags in adjacent messages
from collections import defaultdict
import time

recent_file_shares = defaultdict(list)  # channel_id -> list of {user_id, ts, file_id}
MAX_TIME_WINDOW = 60  # seconds to look for adjacent messages


def clean_old_file_shares():
    """Remove file shares older than MAX_TIME_WINDOW"""
    current_time = time.time()
    for channel_id in list(recent_file_shares.keys()):
        recent_file_shares[channel_id] = [
            fs for fs in recent_file_shares[channel_id]
            if current_time - fs["time"] < MAX_TIME_WINDOW
        ]
        if not recent_file_shares[channel_id]:
            del recent_file_shares[channel_id]


def get_adjacent_messages(channel_id, ts, limit=2):
    """Get messages before and potentially after the given timestamp"""
    try:
        # Get messages around the timestamp
        result = app.client.conversations_history(
            channel=channel_id,
            oldest=str(float(ts) - 1),  # 1 second before
            latest=str(float(ts) + 1),  # 1 second after
            limit=limit + 1,
            inclusive=True
        )
        return result.get("messages", [])
    except Exception as e:
        print(f"Error fetching adjacent messages: {e}")
        return []


def extract_mentions(text):
    """Extract user mentions from text"""
    if not text:
        return []
    return re.findall(r"<@([A-Z0-9]+)>", text)


def classify_message(event):
    """Classify message as file or text"""
    has_files = "files" in event and len(event["files"]) > 0
    if has_files:
        file_types = [f.get("mimetype", "unknown") for f in event["files"]]
        return "file", file_types
    return "text", []


def is_spot(event, channel_id=None):
    """
    Check if a message is a 'spot':
    - Must have at least one file (any type)
    - Must tag at least one user (in same message, previous message, or next message)
    """
    has_file = "files" in event and len(event["files"]) > 0
    
    if not has_file:
        return False, []
    
    # Check for user mentions in the current message
    text = event.get("text", "")
    user_mentions = extract_mentions(text)
    
    if user_mentions:
        print(f"   ✅ Found mentions in same message: {user_mentions}")
        return True, user_mentions
    
    # Check adjacent messages if channel_id is provided
    if channel_id:
        ts = event.get("ts")
        if ts:
            adjacent_msgs = get_adjacent_messages(channel_id, ts)
            print(f"   Checking {len(adjacent_msgs)} adjacent messages")
            
            for msg in adjacent_msgs:
                if msg.get("ts") != ts:  # Don't check the same message again
                    mentions = extract_mentions(msg.get("text", ""))
                    if mentions:
                        print(f"   ✅ Found mentions in adjacent message: {mentions}")
                        return True, mentions
    
    print(f"   ❌ No mentions found in message or adjacent messages")
    return False, []


def is_spot_from_file_shared(file_id, channel_id, user_id):
    """
    Check if a file_shared event is a spot:
    - Any file type counts
    - Must tag at least one user (in same message, previous, or next)
    """
    try:
        print(f"🔍 Checking file {file_id} in channel {channel_id} from user {user_id}")
        
        # Get file info
        file_info = app.client.files_info(file=file_id)
        file_data = file_info["file"]
        
        mimetype = file_data.get("mimetype", "")
        print(f"   File mimetype: {mimetype}")
        
        all_mentions = []
        
        # Check the initial comment/caption that came with the file upload
        initial_comment = file_data.get("initial_comment", {})
        if initial_comment:
            comment_text = initial_comment.get("comment", "")
            print(f"   File caption/comment: {comment_text}")
            mentions = extract_mentions(comment_text)
            if mentions:
                print(f"   ✅ Found mentions in file caption: {mentions}")
                all_mentions.extend(mentions)
        
        # Get the message with the file to check for mentions
        shares = file_data.get("shares", {})
        print(f"   Shares data available: public={bool(shares.get('public'))}, private={bool(shares.get('private'))}")
        
        # Check both public and private channels
        ts = None
        for share_type in ["public", "private"]:
            type_shares = shares.get(share_type, {})
            if channel_id in type_shares:
                share_info = type_shares[channel_id][0]
                ts = share_info.get("ts")
                print(f"   Found in {share_type} channel, timestamp: {ts}")
                break
        
        if ts:
            # Check current message and adjacent messages
            adjacent_msgs = get_adjacent_messages(channel_id, ts, limit=3)
            print(f"   Checking {len(adjacent_msgs)} messages (current + adjacent)")
            
            for msg in adjacent_msgs:
                text = msg.get("text", "")
                mentions = extract_mentions(text)
                if mentions:
                    print(f"   ✅ Found mentions in message at {msg.get('ts')}: {mentions}")
                    all_mentions.extend(mentions)
            
            # Remove duplicates
            all_mentions = list(set(all_mentions))
            
            if all_mentions:
                print(f"   ✅ Total unique mentions found: {all_mentions}")
                return True, all_mentions
            else:
                print(f"   ❌ No mentions found in any adjacent messages")
                # Store this file share to check against future messages
                recent_file_shares[channel_id].append({
                    "user_id": user_id,
                    "ts": ts,
                    "file_id": file_id,
                    "time": time.time()
                })
                print(f"   📝 Stored file share for future matching")
        else:
            print(f"   ❌ Could not find timestamp in shares data")
            print(f"   Shares structure: {shares}")
        
        return False, []
    except Exception as e:
        print(f"❌ Error checking file_shared event: {e}")
        import traceback
        traceback.print_exc()
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


def handle_message_event(event, say):
    """Handle all messages in channels (public or private) the bot is in"""
    # Ignore bot messages and message changes
    if event.get("subtype") is not None:
        return
    
    sender_id = event.get("user")
    channel_id = event.get("channel")
    if not sender_id:
        return
    
    # Clean old file shares periodically
    clean_old_file_shares()
    
    # Classify the message
    msg_type, file_types = classify_message(event)
    print(f"📩 Message classified as '{msg_type}' from {sender_id} in channel {channel_id}")
    if msg_type == "file":
        print(f"   File types: {', '.join(file_types)}")
    
    # Check if this is a spot (message with file)
    is_valid_spot, tagged_users = is_spot(event, channel_id)
    
    if is_valid_spot:
        process_spot(sender_id, tagged_users, channel_id, event.get("ts"))
        return
    
    # If message has no file but has mentions, check for recent file shares
    if msg_type == "text":
        mentions = extract_mentions(event.get("text", ""))
        if mentions and channel_id in recent_file_shares:
            print(f"   📝 Message has mentions, checking recent file shares...")
            # Check if there's a recent file share from the same or different user
            for file_share in recent_file_shares[channel_id]:
                file_user = file_share["user_id"]
                print(f"   🔗 Matching with file from {file_user}")
                process_spot(file_user, mentions, channel_id, file_share.get("ts"))
                # Remove the matched file share
                recent_file_shares[channel_id].remove(file_share)
                return


@app.event("message")
def handle_message(event, say):
    """Handle messages in public channels"""
    handle_message_event(event, say)


# Note: Slack doesn't have a separate event type for private channel messages.
# The "message" event covers both public channels and private channels the bot is in.
# However, if you need to explicitly handle group messages, you can add:
# @app.event("message.groups")
# But typically the @app.event("message") handler will catch all message events
# regardless of channel type when the bot has the appropriate scopes.


def process_spot(sender_id, tagged_users, channel_id=None, ts=None):
    """Process a valid spot - update points in database"""
    num_tagged = len(tagged_users)
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
    
    # Add reaction to message
    if channel_id and ts:
        try:
            app.client.reactions_add(channel=channel_id, timestamp=ts, emoji="eyes")
        except Exception as e:
            print(f"⚠️ Failed to add reaction: {e}")
    
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
    is_valid_spot, tagged_users = is_spot_from_file_shared(file_id, channel_id, user_id)
    
    if is_valid_spot:
        # Get the timestamp from file shares
        shares = app.client.files_info(file=file_id)["file"].get("shares", {})
        ts = None
        for share_type in ["public", "private"]:
            type_shares = shares.get(share_type, {})
            if channel_id in type_shares:
                ts = type_shares[channel_id][0].get("ts")
                break
        process_spot(user_id, tagged_users, channel_id, ts)


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

