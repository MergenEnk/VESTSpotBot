import os
import re
import ssl
from collections import deque
from threading import Lock
from functools import lru_cache
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from database import Database

# Load environment variables from .env file
load_dotenv()

# Fix SSL certificate verification for macOS
ssl._create_default_https_context = ssl._create_unverified_context

# Initialize the app with your tokens
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
db = Database()

# Channel where the bot operates
SPOTTED_CHANNEL = os.environ.get("SPOTTED_CHANNEL_ID")

# Track processed messages to avoid duplicate processing (keeps last 1000 messages)
processed_messages = deque(maxlen=1000)
processed_lock = Lock()


def extract_mentions(text):
    """Extract user IDs from @mentions in text"""
    if not text:
        return []
    # Slack mentions format: <@U12345678>
    mentions = re.findall(r'<@([A-Z0-9]+)>', text)
    return mentions


def has_image(message):
    """Check if message contains an image"""
    if 'files' in message:
        for file in message['files']:
            if file.get('mimetype', '').startswith('image/'):
                return True
    return False


@lru_cache(maxsize=500)
def get_user_name(user_id, token):
    """Cached user name lookup to reduce API calls"""
    try:
        from slack_sdk import WebClient
        client = WebClient(token=token)
        info = client.users_info(user=user_id)
        return info['user']['real_name'] or info['user']['name']
    except Exception as e:
        print(f"Error fetching user name for {user_id}: {e}")
        return None


@app.event("message")
def handle_message(event, say, client):
    """Handle messages in the spotted channel"""
    
    # Only process messages in the designated channel
    if event.get('channel') != SPOTTED_CHANNEL:
        return
    
    # Ignore bot messages and message edits
    if event.get('subtype') in ['bot_message', 'message_changed']:
        return
    
    # Thread-safe deduplication check
    msg_ts = event.get('ts')
    with processed_lock:
        if msg_ts and msg_ts in processed_messages:
            print(f"⏭️  Message {msg_ts} already processed, skipping")
            return
        processed_messages.append(msg_ts)
    
    # ONLY process messages with images (let command handlers deal with text-only messages)
    if not has_image(event):
        return
    
    print(f"📩 Received message event with image: {event}")
    
    spotter_id = event.get('user')
    if not spotter_id:
        print("❌ No user ID in message")
        return
    
    print(f"👤 Spotter: {spotter_id}")
    print("✅ Image detected")
    
    # Extract mentions
    text = event.get('text', '')
    mentioned_users = extract_mentions(text)
    
    print(f"🏷️  Found mentions: {mentioned_users}")
    
    # Remove the spotter from mentions (can't spot yourself)
    mentioned_users = [user for user in mentioned_users if user != spotter_id]
    
    if not mentioned_users:
        print("❌ No valid mentions (or only self-mention)")
        return
    
    # Process all spotted users together
    try:
        # Use cached user lookup
        bot_token = os.environ.get("SLACK_BOT_TOKEN")
        spotter_name = get_user_name(spotter_id, bot_token)
        if not spotter_name:
            spotter_name = spotter_id
        
        spotted_names = []
        for spotted_id in mentioned_users:
            try:
                spotted_name = get_user_name(spotted_id, bot_token)
                if not spotted_name:
                    spotted_name = spotted_id
                
                # Update scores with names
                db.add_point(spotter_id, 1, spotter_name)
                db.add_point(spotted_id, -1, spotted_name)
                
                spotted_names.append(f"<@{spotted_id}>")
                print(f"✅ Spotted {spotted_id}!")
            except Exception as e:
                print(f"Error processing {spotted_id}: {e}")
        
        if spotted_names:
            # React to the message
            client.reactions_add(
                channel=event['channel'],
                timestamp=event['ts'],
                name='eyes'
            )
            
            spotted_list = ", ".join(spotted_names)
            points_earned = len(spotted_names)
            
            # Post confirmation
            say(
                f"📸 *SPOTTED!* {spotted_list} caught by <@{spotter_id}>!\n"
                f"Score update: {spotter_name} +{points_earned} | Tagged users -{len(spotted_names)}",
                thread_ts=event['ts']
            )
    except Exception as e:
        print(f"Error processing spots: {e}")


if __name__ == "__main__":
    print("⚡️ Spotted Bot is starting...")
    print(f"📺 Monitoring channel: {SPOTTED_CHANNEL}")
    print(f"🔑 Bot token: {'✅ Set' if os.environ.get('SLACK_BOT_TOKEN') else '❌ Missing'}")
    print(f"🔑 App token: {'✅ Set' if os.environ.get('SLACK_APP_TOKEN') else '❌ Missing'}")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Spotted Bot is running!")
    handler.start()

