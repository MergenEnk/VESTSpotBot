import os
import re
import ssl
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
                        text = msg.get('text', '')
                        print(f"📝 Message text: {text}")
                        
                        mentioned_users = extract_mentions(text)
                        print(f"🏷️  Found mentions: {mentioned_users}")
                        
                        mentioned_users = [u for u in mentioned_users if u != user_id]
                        
                        if not mentioned_users:
                            print("❌ No valid mentions")
                            return
                        
                        # Process spots
                        for spotted_id in mentioned_users:
                            db.add_point(user_id, 1)
                            db.add_point(spotted_id, -1)
                            
                            try:
                                spotter_info = client.users_info(user=user_id)
                                spotted_info = client.users_info(user=spotted_id)
                                spotter_name = spotter_info['user']['real_name'] or spotter_info['user']['name']
                                spotted_name = spotted_info['user']['real_name'] or spotted_info['user']['name']
                                
                                client.reactions_add(channel=channel_id, timestamp=msg['ts'], name='eyes')
                                
                                say(
                                    f"📸 *SPOTTED!* <@{spotted_id}> was caught by <@{user_id}>!\n"
                                    f"Score update: {spotter_name} +1 | {spotted_name} -1",
                                    thread_ts=msg['ts'],
                                    channel=channel_id
                                )
                                print(f"✅ Spotted {spotted_id}!")
                            except Exception as e:
                                print(f"Error processing spot: {e}")
                        return
    except Exception as e:
        print(f"Error handling file_shared: {e}")


@app.event("message")
def handle_message(event, say, client):
    """Handle messages in the spotted channel"""
    print(f"📩 Received message event: {event}")
    
    # Only process messages in the designated channel
    if event.get('channel') != SPOTTED_CHANNEL:
        print(f"❌ Wrong channel: {event.get('channel')} != {SPOTTED_CHANNEL}")
        return
    
    # Ignore bot messages and message edits
    if event.get('subtype') in ['bot_message', 'message_changed']:
        print(f"❌ Ignoring subtype: {event.get('subtype')}")
        return
    
    spotter_id = event.get('user')
    if not spotter_id:
        print("❌ No user ID in message")
        return
    
    print(f"👤 Spotter: {spotter_id}")
    
    # Check if message has an image
    if not has_image(event):
        print(f"❌ No image found. Files: {event.get('files', 'None')}")
        return
    
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
    
    # Process each spotted user
    for spotted_id in mentioned_users:
        # Update scores
        db.add_point(spotter_id, 1)  # Spotter gets +1
        db.add_point(spotted_id, -1)  # Spotted gets -1
        
        # Get user names
        try:
            spotter_info = client.users_info(user=spotter_id)
            spotted_info = client.users_info(user=spotted_id)
            spotter_name = spotter_info['user']['real_name'] or spotter_info['user']['name']
            spotted_name = spotted_info['user']['real_name'] or spotted_info['user']['name']
            
            # React to the message
            client.reactions_add(
                channel=event['channel'],
                timestamp=event['ts'],
                name='eyes'
            )
            
            # Post confirmation
            say(
                f"📸 *SPOTTED!* <@{spotted_id}> was caught by <@{spotter_id}>!\n"
                f"Score update: {spotter_name} +1 | {spotted_name} -1",
                thread_ts=event['ts']
            )
        except Exception as e:
            print(f"Error processing spot: {e}")


@app.message(re.compile(r"^!leaderboard", re.IGNORECASE))
def show_leaderboard(message, say, client):
    """Show the leaderboard when someone types !leaderboard"""
    if message.get('channel') != SPOTTED_CHANNEL:
        return
    
    scores = db.get_leaderboard()
    
    if not scores:
        say("No one has been spotted yet! 📸")
        return
    
    # Build leaderboard message
    leaderboard_text = "*🏆 SPOTTED LEADERBOARD 🏆*\n\n"
    
    for i, (user_id, score) in enumerate(scores, 1):
        try:
            user_info = client.users_info(user=user_id)
            user_name = user_info['user']['real_name'] or user_info['user']['name']
        except:
            user_name = f"<@{user_id}>"
        
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        leaderboard_text += f"{emoji} *{i}.* {user_name}: {score:+d} points\n"
    
    say(leaderboard_text)


@app.message(re.compile(r"^!myscore", re.IGNORECASE))
def show_my_score(message, say):
    """Show the user's current score"""
    if message.get('channel') != SPOTTED_CHANNEL:
        return
    
    user_id = message.get('user')
    score = db.get_score(user_id)
    
    say(f"<@{user_id}> Your current score: *{score:+d}* points")


@app.message(re.compile(r"^!help", re.IGNORECASE))
def show_help(message, say):
    """Show help message"""
    if message.get('channel') != SPOTTED_CHANNEL:
        return
    
    help_text = """
*📸 SPOTTED BOT HELP 📸*

*How to spot someone:*
Post a photo and @mention the person in the photo. You'll get +1 point and they'll get -1 point!

*Commands:*
• `!leaderboard` - View the full leaderboard
• `!myscore` - Check your current score
• `!help` - Show this help message

*Rules:*
• Must include a photo/image in your message
• Must @mention the person you're spotting
• Can't spot yourself
• Each mention in a photo message counts as a separate spot
"""
    say(help_text)


if __name__ == "__main__":
    print("⚡️ Spotted Bot is starting...")
    print(f"📺 Monitoring channel: {SPOTTED_CHANNEL}")
    print(f"🔑 Bot token: {'✅ Set' if os.environ.get('SLACK_BOT_TOKEN') else '❌ Missing'}")
    print(f"🔑 App token: {'✅ Set' if os.environ.get('SLACK_APP_TOKEN') else '❌ Missing'}")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Spotted Bot is running!")
    handler.start()

