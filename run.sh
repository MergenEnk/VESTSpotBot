#!/bin/bash

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if required env vars are set
if [ -z "$SLACK_BOT_TOKEN" ] || [ -z "$SLACK_APP_TOKEN" ] || [ -z "$SPOTTED_CHANNEL_ID" ]; then
    echo "❌ Error: Missing required environment variables"
    echo "Please create a .env file with:"
    echo "  SLACK_BOT_TOKEN"
    echo "  SLACK_APP_TOKEN"
    echo "  SPOTTED_CHANNEL_ID"
    exit 1
fi

# Run the bot
python bot.py

