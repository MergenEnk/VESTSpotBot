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

### 2. Slack App Setup (Part 1 - Before Deployment)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Choose "From scratch", name it "Spotted Bot"
3. **Add Bot Scopes**:
   - Go to OAuth & Permissions → Scopes
   - Add these Bot Token Scopes:
     - `channels:history` (read messages in public channels)
     - `channels:read` (view basic channel info)
     - `files:read` (access file info)
     - `users:read` (view user names)
4. **Get Signing Secret**:
   - Go to Settings → Basic Information → App Credentials
   - Copy the "Signing Secret"
   - Save this as your `SLACK_SIGNING_SECRET`
5. **Install to Workspace**:
   - Go to OAuth & Permissions
   - Click "Install to Workspace"
   - Save the Bot User OAuth Token as your `SLACK_BOT_TOKEN`

**Note**: You'll configure Event Subscriptions AFTER deploying (need the public URL first)

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
   - `SLACK_BOT_TOKEN` (from step 2.5)
   - `SLACK_SIGNING_SECRET` (from step 2.4)
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
5. Deploy! Railway will automatically:
   - Detect the Procfile
   - Assign a public URL (e.g., `https://your-app.railway.app`)
   - Set the `PORT` environment variable

**Important**: Copy your Railway public URL for the next step!

### 5. Slack App Setup (Part 2 - After Deployment)

1. Go back to your Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. **Enable Event Subscriptions**:
   - Go to Event Subscriptions
   - Toggle on "Enable Events"
   - Enter Request URL: `https://your-railway-url.railway.app/slack/events`
   - Slack will verify the URL (should show ✓ Verified)
   - Subscribe to bot events:
     - `message.channels` (for regular messages)
     - `file_shared` (for file uploads)
   - Click "Save Changes"
3. **Reinstall the app** (required after adding event subscriptions):
   - Go to OAuth & Permissions
   - Click "Reinstall to Workspace"
4. **Invite bot to your channel**:
   - In Slack, type `/invite @Spotted Bot` in your desired channel

**Note**: Railway's free tier is perfect for this bot with HTTP webhooks - fully scalable and production-ready!

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

1. Slack sends HTTP POST requests to your webhook (`/slack/events`) when messages are posted
2. Bot receives events for all messages in channels it's invited to (`message` and `file_shared`)
3. Every message is classified as "file" or "text" and logged
4. For each message, checks if it's a "spot":
   - Has at least one image file (checks MIME type)
   - Has at least one user mention (looks for `<@USER_ID>`)
5. If it's a spot:
   - Fetches usernames from Slack API
   - Extracts all tagged users via regex
   - Updates Supabase: sender gets +1 per tag, tagged users get -1
6. Database uses upsert to create users automatically on first spot

## Features

- ✅ HTTP webhook-based (fully scalable)
- ✅ Gunicorn multi-worker support for concurrency
- ✅ Handles both `message` and `file_shared` events
- ✅ Auto-creates users in database with usernames
- ✅ Classifies every message as "file" or "text"
- ✅ Supports multiple images and multiple tags
- ✅ No 1-1 ratio required (1 image can tag many users)
- ✅ Health check endpoint for monitoring
- ✅ Production-ready with proper error handling

## Troubleshooting

**Bot doesn't respond:**
- Make sure bot is invited to the channel (`/invite @Spotted Bot`)
- Check that Event Subscriptions URL is verified in Slack app settings
- Verify `message.channels` and `file_shared` event subscriptions are active
- Check Railway deployment logs for errors
- Test the health endpoint: `https://your-url.railway.app/health`

**Database errors:**
- Verify Supabase credentials are correct
- Make sure you ran the SQL setup script
- Check Supabase project isn't paused (free tier auto-pauses after inactivity)

**Deployment issues:**
- Check Railway logs for errors
- Ensure all environment variables are set (SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SUPABASE_URL, SUPABASE_KEY)
- Verify Python version matches runtime.txt
- Make sure the web service is running (not worker)
- Test `/health` endpoint returns 200 OK

**Event URL verification fails:**
- Make sure the app is deployed and accessible
- Check that SLACK_SIGNING_SECRET is correct
- Verify no firewall blocking Railway's domain
- Check Railway logs during verification attempt

## License

MIT

