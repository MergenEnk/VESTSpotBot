# Spotted Leaderboard Bot

A lightweight Slack bot that tracks "spots" - messages with images that tag other users. Taggers earn points, tagged users lose points.

## What's a Spot?

A message is a "spot" if it contains:
- **At least one image file**
- **At least one tagged user** (@mention)

When a spot is detected:
- The sender gets **+1 point per person tagged**
- Each tagged user gets **-1 point**

## Setup

### 1. Supabase Setup

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to SQL Editor and run the contents of `supabase_setup.sql`
4. Get your credentials from Settings → API:
   - `SUPABASE_URL` (Project URL)
   - `SUPABASE_KEY` (anon/public key)

### 2. Slack App Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Choose "From scratch", name it "Spotted Bot"
3. **Enable Socket Mode**:
   - Go to Settings → Socket Mode
   - Toggle on "Enable Socket Mode"
   - Generate an app-level token with `connections:write` scope
   - Save this as your `SLACK_APP_TOKEN`
4. **Add Bot Scopes**:
   - Go to OAuth & Permissions → Scopes
   - Add these Bot Token Scopes:
     - `channels:history` (read messages in public channels)
     - `channels:read` (view basic channel info)
     - `files:read` (access file info)
     - `users:read` (view user names)
5. **Enable Events**:
   - Go to Event Subscriptions
   - Toggle on "Enable Events"
   - Subscribe to bot events: `message.channels`
6. **Install to Workspace**:
   - Go to OAuth & Permissions
   - Click "Install to Workspace"
   - Save the Bot User OAuth Token as your `SLACK_BOT_TOKEN`
7. **Invite bot to your channel**:
   - In Slack, type `/invite @Spotted Bot` in your desired channel

### 3. Local Development

```bash
# Clone and navigate to the project
cd Spotted_Leaderboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env.example to .env and fill in your credentials
cp env.example .env

# Run the bot
python main.py  # or python bot.py
```

### 4. Railway Deployment

1. Create account at [railway.app](https://railway.app)
2. Create new project → Deploy from GitHub
3. Connect your repository
4. Add environment variables in Railway dashboard:
   - `SLACK_BOT_TOKEN`
   - `SLACK_APP_TOKEN`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
5. Deploy! Railway will automatically detect the Procfile

**Note**: The free tier on Railway is perfect for this bot since it uses Socket Mode (no webhooks) and minimal resources.

## Project Structure

```
├── bot.py              # Main bot logic and event handlers
├── database.py         # Supabase database operations
├── requirements.txt    # Python dependencies
├── Procfile           # Railway deployment config
├── runtime.txt        # Python version specification
├── supabase_setup.sql # Database schema
└── README.md          # This file
```

## How It Works

1. Bot listens to all messages in channels it's invited to
2. For each message, checks if it's a "spot":
   - Has at least one image file (checks MIME type)
   - Has at least one user mention (looks for `<@USER_ID>`)
3. If it's a spot:
   - Extracts all tagged users via regex
   - Updates Supabase: sender gets +1 per tag, tagged users get -1
4. Database uses upsert to create users automatically on first spot

## Features

- ✅ Lightweight (runs perfectly on free tier)
- ✅ Socket Mode (no public URL needed)
- ✅ Auto-creates users in database
- ✅ Supports multiple images and multiple tags
- ✅ No 1-1 ratio required (1 image can tag many users)
- ✅ Simple error handling with console logging

## Troubleshooting

**Bot doesn't respond:**
- Make sure bot is invited to the channel (`/invite @Spotted Bot`)
- Check that Socket Mode is enabled
- Verify `message.channels` event subscription is active

**Database errors:**
- Verify Supabase credentials are correct
- Make sure you ran the SQL setup script
- Check Supabase project isn't paused (free tier auto-pauses after inactivity)

**Deployment issues:**
- Check Railway logs for errors
- Ensure all 4 environment variables are set
- Verify Python version matches runtime.txt

## License

MIT

