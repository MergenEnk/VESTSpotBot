"""
Main entry point for local development
Loads .env file and starts the Flask web server
"""
from dotenv import load_dotenv
from bot import flask_app

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Start the Flask web server
    import os
    port = int(os.environ.get("PORT", 3000))
    print(f"⚡️ Spotted Bot is running on port {port}!")
    flask_app.run(host="0.0.0.0", port=port, debug=True)

