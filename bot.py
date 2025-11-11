import os
import re
import ssl
from collections import deque
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


@app.event("file_shared")
def handle_file_shared(event, client, say):
    """Handle file_shared events (Slack often sends this for image uploads)"""
    print(f"📁 Received file_shared event: {event}")
    
    file_id = event.get('file_id')
    channel_id = event.get('channel_id')
    user_id = event.get('user_id')
    
    if channel_id != SPOTTED_CHANNEL:
        print(f"❌ File shared in wrong channel: {channel_id}")
        return
    
    try:
        # Get file info
        file_info = client.files_info(file=file_id)
        file = file_info['file']
        
        # Check if it's an image
        if not file.get('mimetype', '').startswith('image/'):
            print(f"❌ File is not an image: {file.get('mimetype')}")
            return
        
        print(f"✅ Image file shared by {user_id}")
        
        # Get the message to extract mentions
        # Slack doesn't include the message text in file_shared, so we need to get recent messages
        history = client.conversations_history(channel=channel_id, limit=5)
        
        for msg in history['messages']:
            if msg.get('user') == user_id and 'files' in msg:
                for f in msg['files']:
                    if f['id'] == file_id:
                        # Found the message with this file
                        msg_ts = msg['ts']
                        
                        # Check if we've already processed this message
                        if msg_ts in processed_messages:
                            print(f"⏭️  Message {msg_ts} already processed, skipping")
                            return
                        
                        text = msg.get('text', '')
                        print(f"📝 Message text: {text}")
                        
                        mentioned_users = extract_mentions(text)
                        print(f"🏷️  Found mentions: {mentioned_users}")
                        
                        mentioned_users = [u for u in mentioned_users if u != user_id]
                        
                        if not mentioned_users:
                            print("❌ No valid mentions")
                            return
                        
                        # Count images in message
                        image_count = sum(1 for file in msg.get('files', []) if file.get('mimetype', '').startswith('image/'))
                        print(f"📷 Found {image_count} image(s) in message")
                        
                        if image_count == 0:
                            print("❌ No images in message")
                            return
                        
                        # Mark message as processed
                        processed_messages.append(msg_ts)
                        
                        # Process all spots together
                        try:
                            spotter_info = client.users_info(user=user_id)
                            spotter_name = spotter_info['user']['real_name'] or spotter_info['user']['name']
                            
                            spotted_names = []
                            for spotted_id in mentioned_users:
                                try:
                                    spotted_info = client.users_info(user=spotted_id)
                                    spotted_name = spotted_info['user']['real_name'] or spotted_info['user']['name']
                                    
                                    # Update scores with names
                                    db.add_point(user_id, 1, spotter_name)
                                    db.add_point(spotted_id, -1, spotted_name)
                                    
                                    spotted_names.append(f"<@{spotted_id}>")
                                    print(f"✅ Spotted {spotted_id}!")
                                except Exception as e:
                                    print(f"Error processing {spotted_id}: {e}")
                            
                            if spotted_names:
                                client.reactions_add(channel=channel_id, timestamp=msg['ts'], name='eyes')
                                
                                spotted_list = ", ".join(spotted_names)
                                points_earned = len(spotted_names)
                                
                                say(
                                    f"📸 *SPOTTED!* {spotted_list} caught by <@{user_id}>!\n"
                                    f"Score update: {spotter_name} +{points_earned} | Tagged users -{len(spotted_names)}",
                                    thread_ts=msg['ts'],
                                    channel=channel_id
                                )
                        except Exception as e:
                            print(f"Error processing spots: {e}")
                        return
    except Exception as e:
        print(f"Error handling file_shared: {e}")


@app.event("message")
def handle_message(event, say, client):
    """Handle messages in the spotted channel"""
    
    # Only process messages in the designated channel
    if event.get('channel') != SPOTTED_CHANNEL:
        return
    
    # Ignore bot messages, message edits, and file_share subtype
    # file_share is handled by file_shared event handler to avoid duplicates
    if event.get('subtype') in ['bot_message', 'message_changed', 'file_share']:
        return
    
    # Check if message already processed (avoid race conditions)
    msg_ts = event.get('ts')
    if msg_ts and msg_ts in processed_messages:
        print(f"⏭️  Message {msg_ts} already processed, skipping")
        return
    
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
    
    # Mark message as processed to avoid duplicates
    processed_messages.append(msg_ts)
    
    # Process all spotted users together
    try:
        spotter_info = client.users_info(user=spotter_id)
        spotter_name = spotter_info['user']['real_name'] or spotter_info['user']['name']
        
        spotted_names = []
        for spotted_id in mentioned_users:
            try:
                spotted_info = client.users_info(user=spotted_id)
                spotted_name = spotted_info['user']['real_name'] or spotted_info['user']['name']
                
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

