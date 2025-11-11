import os
import ssl
import time
from threading import Thread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix SSL for macOS
ssl._create_default_https_context = ssl._create_unverified_context


def run_bot():
    """Run the Slack bot"""
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
        
        # Import bot to get the configured app
        import bot
        
        print("⚡️ Spotted Bot is starting...")
        print(f"📺 Monitoring channel: {os.environ.get('SPOTTED_CHANNEL_ID')}")
        print(f"🔑 Bot token: {'✅ Set' if os.environ.get('SLACK_BOT_TOKEN') else '❌ Missing'}")
        print(f"🔑 App token: {'✅ Set' if os.environ.get('SLACK_APP_TOKEN') else '❌ Missing'}")
        
        handler = SocketModeHandler(bot.app, os.environ.get("SLACK_APP_TOKEN"))
        print("⚡️ Spotted Bot is running!")
        handler.start()
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")
        print("🌐 API will continue running...")


def run_api():
    """Run the Flask API"""
    from api import app
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 API starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    print("🚀 Starting Spotted Leaderboard System...\n")
    
    # Start bot in separate thread
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Give bot a moment to start
    time.sleep(2)
    
    # Run API in main thread (so Railway can detect it)
    print("🌐 Starting API server (main thread)...")
    run_api()

