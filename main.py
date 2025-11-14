"""
Main entry point for local development
Loads .env file and starts the bot
"""
from dotenv import load_dotenv
from bot import start

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Start the bot
    start()

