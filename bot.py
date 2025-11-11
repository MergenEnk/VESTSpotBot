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

# Track processed messages to avoid duplicate processing
processed_messages = set()


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
                        processed_messages.add(msg_ts)
                        
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


# TEMPORARILY DISABLED FOR TESTING
# @app.event("message")
def handle_message_disabled(event, say, client):
    """Handle messages in the spotted channel"""
    
    # Only process messages in the designated channel
    if event.get('channel') != SPOTTED_CHANNEL:
        return
    
    # Ignore bot messages and message edits
    if event.get('subtype') in ['bot_message', 'message_changed']:
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


@app.message(re.compile(r"^!leaderboard", re.IGNORECASE))
def show_leaderboard(message, say, client):
    """Show the leaderboard when someone types !leaderboard"""
    print(f"🏆 !leaderboard command received from {message.get('user')}")
    if message.get('channel') != SPOTTED_CHANNEL:
        print(f"❌ Wrong channel for !leaderboard: {message.get('channel')}")
        return
    
    scores = db.get_leaderboard()
    
    if not scores:
        say("No one has been spotted yet! 📸")
        return
    
    # Build leaderboard message
    leaderboard_text = "*🏆 SPOTTED LEADERBOARD 🏆*\n\n"
    
    for i, (user_id, user_name, score) in enumerate(scores, 1):
        display_name = user_name or f"<@{user_id}>"
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        leaderboard_text += f"{emoji} *{i}.* {display_name}: {score:+d} points\n"
    
    say(leaderboard_text)


@app.message(re.compile(r"^!myscore", re.IGNORECASE))
def show_my_score(message, say):
    """Show the user's current score"""
    print(f"📊 !myscore command received from {message.get('user')}")
    if message.get('channel') != SPOTTED_CHANNEL:
        print(f"❌ Wrong channel for !myscore: {message.get('channel')}")
        return
    
    user_id = message.get('user')
    score = db.get_score(user_id)
    
    say(f"<@{user_id}> Your current score: *{score:+d}* points")


@app.message(re.compile(r"^!adjust\s+<@([A-Z0-9]+)>\s+([-+]?\d+)", re.IGNORECASE))
def adjust_score(message, say, client):
    """Admin command to manually adjust someone's score"""
    print(f"⚖️ !adjust command received: {message.get('text')}")
    if message.get('channel') != SPOTTED_CHANNEL:
        print(f"❌ Wrong channel for !adjust: {message.get('channel')}")
        return
    
    admin_user = message.get('user')
    match = re.search(r'^!adjust\s+<@([A-Z0-9]+)>\s+([-+]?\d+)', message.get('text', ''), re.IGNORECASE)
    
    if not match:
        return
    
    target_user = match.group(1)
    adjustment = int(match.group(2))
    
    try:
        # Get user names
        target_info = client.users_info(user=target_user)
        target_name = target_info['user']['real_name'] or target_info['user']['name']
        
        admin_info = client.users_info(user=admin_user)
        admin_name = admin_info['user']['real_name'] or admin_info['user']['name']
        
        # Update score
        db.add_point(target_user, adjustment, target_name)
        new_score = db.get_score(target_user)
        
        say(
            f"⚖️ *Score Adjusted*\n"
            f"<@{target_user}>'s score adjusted by {adjustment:+d} by {admin_name}\n"
            f"New score: {new_score:+d} points"
        )
        print(f"✅ {admin_name} adjusted {target_name}'s score by {adjustment}")
    except Exception as e:
        say(f"❌ Error adjusting score: {e}")
        print(f"Error adjusting score: {e}")


@app.message(re.compile(r"^!help", re.IGNORECASE))
def show_help(message, say):
    """Show help message"""
    print(f"🆘 !help command received from {message.get('user')}")
    if message.get('channel') != SPOTTED_CHANNEL:
        print(f"❌ Wrong channel for !help: {message.get('channel')}")
        return
    
    help_text = """
*📸 SPOTTED BOT HELP 📸*

*How to spot someone:*
Post a photo and @mention people in the photo. You get +1 point per person tagged, they each get -1 point!

*Examples:*
• "Look who I found! @john @sarah" (You: +2, John: -1, Sarah: -1)
• "Caught @mike slacking" (You: +1, Mike: -1)

*Commands:*
• `!leaderboard` - View the full leaderboard
• `!myscore` - Check your current score
• `!help` - Show this help message

*Rules:*
• Must include at least one photo/image
• Can tag multiple people in one message (all assumed to be in the photo(s))
• Can't spot yourself
• Each tagged person counts as a spot

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

