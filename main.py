import os
import ssl
import time
import traceback
from threading import Thread, Event
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix SSL for macOS (only if explicitly enabled)
if os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true":
    ssl._create_default_https_context = ssl._create_unverified_context
    print("⚠️  SSL verification disabled")

# Global flag for graceful shutdown
shutdown_event = Event()


def run_bot_with_restart():
    """Run the Slack bot with automatic restart on failure"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        if shutdown_event.is_set():
            print("🛑 Bot shutdown requested")
            break
            
        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            
            # Import bot to get the configured app
            import bot
            
            print(f"⚡️ Spotted Bot is starting (attempt {attempt + 1}/{max_retries})...")
            print(f"📺 Monitoring channel: {os.environ.get('SPOTTED_CHANNEL_ID')}")
            print(f"🔑 Bot token: {'✅ Set' if os.environ.get('SLACK_BOT_TOKEN') else '❌ Missing'}")
            print(f"🔑 App token: {'✅ Set' if os.environ.get('SLACK_APP_TOKEN') else '❌ Missing'}")
            
            handler = SocketModeHandler(bot.app, os.environ.get("SLACK_APP_TOKEN"))
            print("⚡️ Spotted Bot is running!")
            handler.start()
            
            # If we reach here, handler.start() was interrupted
            print("⚠️  Bot handler stopped")
            
        except KeyboardInterrupt:
            print("🛑 Bot interrupted by user")
            shutdown_event.set()
            break
        except Exception as e:
            print(f"❌ Bot failed: {e}")
            print(traceback.format_exc())
            
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Bot failed after {max_retries} attempts. Giving up.")
                print("🌐 API will continue running...")
                break


def run_api():
    """Run the Flask API with error handling"""
    try:
        from api import app
        port = int(os.environ.get('PORT', 5000))
        print(f"🌐 API starting on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ API failed to start: {e}")
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    print("🚀 Starting Spotted Leaderboard System...\n")
    
    # Start bot in separate thread (non-daemon so it can restart)
    bot_thread = Thread(target=run_bot_with_restart, daemon=False, name="BotThread")
    bot_thread.start()
    
    # Give bot a moment to start
    time.sleep(2)
    
    # Run API in main thread (so deployment platforms can detect it)
    print("🌐 Starting API server (main thread)...")
    try:
        run_api()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        shutdown_event.set()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        shutdown_event.set()
        raise

