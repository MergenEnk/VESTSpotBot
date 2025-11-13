import os
import re
import ssl
import time
from collections import deque
from threading import Lock
from functools import lru_cache
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from database import Database

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables
required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SPOTTED_CHANNEL_ID", "SUPABASE_URL", "SUPABASE_KEY"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Fix SSL certificate verification for macOS (only if needed)
if os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true":
    ssl._create_default_https_context = ssl._create_unverified_context
    print("⚠️  SSL verification disabled")

# Initialize the app with your tokens
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
db = Database()

# Channel where the bot operates
SPOTTED_CHANNEL = os.environ.get("SPOTTED_CHANNEL_ID")

# Track processed messages to avoid duplicate processing (keeps last 1000 messages)
processed_messages = deque(maxlen=1000)
processed_lock = Lock()


def extract_mentions(text):
    """Extract user IDs from @mentions in text with validation"""
    if not text:
        return []
    # Slack mentions format: <@U12345678>
    # Validate that user IDs are alphanumeric and reasonable length
    mentions = re.findall(r'<@([A-Z0-9]+)>', text)
    # Filter out invalid IDs (must be 9-11 chars for Slack user IDs)
    valid_mentions = [m for m in mentions if 9 <= len(m) <= 11 and m.startswith('U')]
    return valid_mentions


def has_image(message):
    """Check if message contains an image"""
    if 'files' in message:
        for file in message['files']:
            if file.get('mimetype', '').startswith('image/'):
                return True
    return False


@lru_cache(maxsize=500)
def get_user_name(user_id, token):
    """Cached user name lookup to reduce API calls with retry logic"""
    from slack_sdk import WebClient
    client = WebClient(token=token)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            info = client.users_info(user=user_id)
            return info['user']['real_name'] or info['user']['name']
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                continue
            print(f"Error fetching user name for {user_id} after {max_retries} attempts: {e}")
            return None
    return None


@app.event("file_shared")
def handle_file_shared(event):
    """
    Acknowledge file_shared events to prevent warnings.
    The message event contains all needed info, so we don't process here.
    """
    print(f"📁 file_shared event received: file_id={event.get('file_id')}, user={event.get('user_id')}")
    pass


# Catch-all for debugging - log ALL events we receive
@app.event({"type": ".*"})
def log_all_events(event, logger):
    """Log all events for debugging purposes"""
    event_type = event.get("type", "unknown")
    event_subtype = event.get("subtype", "none")
    print(f"📥 Event received: type={event_type}, subtype={event_subtype}, channel={event.get('channel', 'N/A')}")


@app.event("message")
def handle_message(event, say, client):
    """Handle messages in the spotted channel with comprehensive validation"""
    
    # Log EVERY message event we receive for debugging
    print(f"\n{'='*60}")
    print(f"🔔 MESSAGE EVENT RECEIVED")
    print(f"{'='*60}")
    
    # Validate event structure
    if not isinstance(event, dict):
        print("❌ Invalid event structure")
        return
    
    print(f"Channel: {event.get('channel')} (Target: {SPOTTED_CHANNEL})")
    print(f"User: {event.get('user')}")
    print(f"Timestamp: {event.get('ts')}")
    print(f"Subtype: {event.get('subtype', 'None')}")
    print(f"Text: {event.get('text', '')[:100]}")
    print(f"Has 'files' key: {'files' in event}")
    if 'files' in event:
        print(f"Number of files: {len(event.get('files', []))}")
        for i, f in enumerate(event.get('files', [])):
            print(f"  File {i+1}: {f.get('mimetype', 'unknown')} - {f.get('name', 'unnamed')}")
    
    # Only process messages in the designated channel
    if event.get('channel') != SPOTTED_CHANNEL:
        print("⏭️  Wrong channel, ignoring")
        return
    
    # Ignore bot messages and message edits
    if event.get('subtype') in ['bot_message', 'message_changed', 'message_deleted']:
        print(f"⏭️  Ignoring subtype: {event.get('subtype')}")
        return
    
    # Thread-safe deduplication check
    msg_ts = event.get('ts')
    if not msg_ts:
        print("❌ No timestamp in message")
        return
    
    with processed_lock:
        if msg_ts in processed_messages:
            print(f"⏭️  Message {msg_ts} already processed, skipping")
            return
        processed_messages.append(msg_ts)
    
    print(f"✅ Passed all initial checks, proceeding to file check...")
    
    # Check if message has images
    has_files = has_image(event)
    print(f"Initial file check: {has_files}")
    
    # If no files immediately, wait briefly for them to attach (timing issue)
    if not has_files:
        print(f"⏳ No files detected immediately, waiting 2 seconds and retrying...")
        time.sleep(2.0)
        
        try:
            # Re-fetch the message to get updated file attachments
            print(f"🔄 Fetching message history to check for files...")
            result = client.conversations_history(
                channel=event['channel'],
                latest=msg_ts,
                limit=1,
                inclusive=True
            )
            
            if result.get('messages') and len(result['messages']) > 0:
                event = result['messages'][0]  # Use updated event
                print(f"📥 Refetched message, checking for files...")
                print(f"  Has 'files' key: {'files' in event}")
                if 'files' in event:
                    print(f"  Number of files: {len(event.get('files', []))}")
                    for i, f in enumerate(event.get('files', [])):
                        print(f"    File {i+1}: {f.get('mimetype', 'unknown')}")
                
                has_files = has_image(event)
                if has_files:
                    print(f"✅ Files detected after retry!")
                else:
                    print(f"❌ Still no files after retry - this is a text-only message")
            else:
                print(f"❌ Could not refetch message")
        except Exception as e:
            print(f"⚠️  Could not retry fetch: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"✅ Files detected immediately")
    
    # ONLY process messages with images
    if not has_files:
        print(f"⏭️  No images found, skipping message")
        return
    
    print(f"\n{'='*60}")
    print(f"📩 PROCESSING SPOT")
    print(f"{'='*60}")
    
    spotter_id = event.get('user')
    if not spotter_id or not isinstance(spotter_id, str):
        print("❌ No valid user ID in message")
        return
    
    # Validate spotter ID format
    if not (9 <= len(spotter_id) <= 11 and spotter_id.startswith('U')):
        print(f"❌ Invalid spotter ID format: {spotter_id}")
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
    
    # Limit to 10 users per spot to prevent abuse
    if len(mentioned_users) > 10:
        print(f"⚠️  Too many mentions ({len(mentioned_users)}), limiting to 10")
        try:
            say(
                f"⚠️  You can only spot up to 10 people at once. Processing first 10 mentions.",
                thread_ts=event['ts']
            )
        except:
            pass
        mentioned_users = mentioned_users[:10]
    
    # Process all spotted users together
    try:
        # Use cached user lookup
        bot_token = os.environ.get("SLACK_BOT_TOKEN")
        spotter_name = get_user_name(spotter_id, bot_token)
        if not spotter_name:
            spotter_name = spotter_id
        
        spotted_names = []
        failed_updates = []
        
        for spotted_id in mentioned_users:
            try:
                spotted_name = get_user_name(spotted_id, bot_token)
                if not spotted_name:
                    spotted_name = spotted_id
                
                # Update scores with names - wrapped in try/catch per user
                try:
                    db.add_point(spotter_id, 1, spotter_name)
                    db.add_point(spotted_id, -1, spotted_name)
                    spotted_names.append(f"<@{spotted_id}>")
                    print(f"✅ Spotted {spotted_id}!")
                except Exception as db_error:
                    print(f"❌ Database error for {spotted_id}: {db_error}")
                    failed_updates.append(spotted_id)
            except Exception as e:
                print(f"❌ Error processing {spotted_id}: {e}")
                failed_updates.append(spotted_id)
        
        if spotted_names:
            # React to the message with retry
            try:
                for attempt in range(3):
                    try:
                        client.reactions_add(
                            channel=event['channel'],
                            timestamp=event['ts'],
                            name='eyes'
                        )
                        break
                    except Exception as e:
                        if attempt < 2:
                            time.sleep(0.5 * (attempt + 1))
                        else:
                            print(f"⚠️  Failed to add reaction: {e}")
            except Exception as e:
                print(f"⚠️  Reaction failed: {e}")
            
            spotted_list = ", ".join(spotted_names)
            points_earned = len(spotted_names)
            
            # Post confirmation with retry
            response_msg = f"📸 *SPOTTED!* {spotted_list} caught by <@{spotter_id}>!\n" \
                          f"Score update: {spotter_name} +{points_earned} | Tagged users -{len(spotted_names)}"
            
            if failed_updates:
                response_msg += f"\n⚠️  Failed to update: {', '.join([f'<@{uid}>' for uid in failed_updates])}"
            
            try:
                for attempt in range(3):
                    try:
                        say(response_msg, thread_ts=event['ts'])
                        break
                    except Exception as e:
                        if attempt < 2:
                            time.sleep(0.5 * (attempt + 1))
                        else:
                            print(f"⚠️  Failed to post response: {e}")
            except Exception as e:
                print(f"⚠️  Response failed: {e}")
        elif failed_updates:
            # All updates failed
            try:
                say(
                    f"⚠️  Failed to process spotted users. Please try again or contact an admin.",
                    thread_ts=event['ts']
                )
            except Exception as e:
                print(f"⚠️  Failed to post error message: {e}")
    except Exception as e:
        print(f"❌ Critical error processing spots: {e}")
        # Try to notify user of failure
        try:
            say(
                f"❌ An error occurred while processing your spot. Please try again.",
                thread_ts=event.get('ts')
            )
        except:
            pass  # Best effort notification


if __name__ == "__main__":
    print("⚡️ Spotted Bot is starting...")
    print(f"📺 Monitoring channel: {SPOTTED_CHANNEL}")
    print(f"🔑 Bot token: {'✅ Set' if os.environ.get('SLACK_BOT_TOKEN') else '❌ Missing'}")
    print(f"🔑 App token: {'✅ Set' if os.environ.get('SLACK_APP_TOKEN') else '❌ Missing'}")
    
    # Create handler with trace enabled for debugging
    handler = SocketModeHandler(
        app=app,
        app_token=os.environ.get("SLACK_APP_TOKEN"),
        trace_enabled=True
    )
    
    # Force fresh connection
    if hasattr(handler, 'client'):
        handler.client.wss_uri = None
    
    print("⚡️ Spotted Bot is running!")
    print("🔌 WebSocket connection active - waiting for events...")
    handler.start()

