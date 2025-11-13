# 📸 Spotted Leaderboard Bot

A Slack bot that tracks when users get "spotted" in photos and maintains a competitive leaderboard.

## How It Works

1. **Post a photo** in the designated channel
2. **@mention people** in the photo (can tag multiple people)
3. **Scoring:**
   - Person who posted: **+1 point per person tagged**
   - Each person tagged: **-1 point**
   
**Example:** Post a photo and tag @john @sarah → You get +2, John gets -1, Sarah gets -1

## Setup Instructions

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name it (e.g., "Spotted Bot") and select your workspace

### 2. Configure OAuth & Permissions

Go to **OAuth & Permissions** and add these Bot Token Scopes:
- `channels:history` - Read messages in channels
- `channels:read` - View basic channel info
- `chat:write` - Send messages
- `files:read` - View files shared in channels (required for file_shared events)
- `reactions:write` - Add emoji reactions
- `users:read` - View people in the workspace

Install the app to your workspace and copy the **Bot User OAuth Token** (starts with `xoxb-`)

> **Important:** After adding scopes, you must reinstall the app for permissions to take effect!

### 3. Enable Socket Mode

1. Go to **Socket Mode** in your app settings
2. Enable Socket Mode
3. Generate an **App-Level Token** with `connections:write` scope
4. Copy the token (starts with `xapp-`)

### 4. Subscribe to Events

1. Go to **Event Subscriptions**
2. Enable Events
3. Under **Subscribe to bot events**, add:
   - `message.channels`
   - `file_shared`
4. Save changes

> **Note:** Both events are needed. The bot ignores `file_shared` but subscribing to it prevents warnings.

### 5. Get Your Channel ID

1. Open Slack and go to the channel where you want the bot
2. Click the channel name → scroll down
3. Copy the Channel ID (starts with `C`)

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

### 7. Configure Environment

Create a `.env` file (or export these variables):

```bash
export SLACK_BOT_TOKEN=xoxb-your-bot-token
export SLACK_APP_TOKEN=xapp-your-app-level-token
export SPOTTED_CHANNEL_ID=C1234567890
export SUPABASE_URL=https://xxxxx.supabase.co
export SUPABASE_KEY=your-supabase-key
```

Or create a `.env` file:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-level-token
SPOTTED_CHANNEL_ID=C1234567890
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-supabase-key
```

> **Note:** Get your Supabase credentials from [supabase.com](https://supabase.com) → Your Project → Settings → API

### 8. Run the Bot

```bash
python bot.py
```

You should see: `⚡️ Spotted Bot is running!`

### 9. Add Bot to Channel

In Slack, invite the bot to your channel:
```
/invite @SpottedBot
```

## Usage Examples

**Single person:**
```
[image.jpg]
Caught @john slacking off! 😂
```

**Bot responds:**
```
📸 SPOTTED! @john caught by @sarah!
Score update: sarah +1 | Tagged users -1
```

**Multiple people:**
```
[image.jpg]
Look who showed up! @john @mike @lisa
```

**Bot responds:**
```
📸 SPOTTED! @john, @mike, @lisa caught by @sarah!
Score update: sarah +3 | Tagged users -3
```

## Database

Scores are stored in **Supabase** (PostgreSQL) for persistent cloud storage that survives redeployments.

### Setup Supabase

See **[SUPABASE_MIGRATION.md](SUPABASE_MIGRATION.md)** for detailed setup instructions.

**Quick setup:**
1. Create a free [Supabase](https://supabase.com) project
2. Run `supabase_setup.sql` in the SQL Editor
3. Add `SUPABASE_URL` and `SUPABASE_KEY` to your environment variables
4. Done! Data now persists across deployments

## Webapp Integration (Hybrid Approach)

Want to visualize the leaderboard? Your webapp fetches **directly from Supabase** (no API middleman needed)!

**Architecture:**
- **Bot** → Writes to Supabase
- **Webapp** → Reads from Supabase directly
- **Flask API** → Health check only (for deployment platforms)

**Example:** See `example_webapp.html` for a beautiful working demo!

**In your webapp:**
```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Fetch leaderboard
const { data } = await supabase
  .from('scores')
  .select('user_id, user_name, score')
  .order('score', { ascending: false });
```

**Benefits:**
- ✅ Simpler (no API routes to maintain)
- ✅ Real-time updates (Supabase subscriptions)
- ✅ Better performance (direct DB access)
- ✅ Secure (Row Level Security)

See `API_GUIDE.md` for full integration details and security setup.

## Cloud Deployment (Run 24/7)

### Option 1: Railway (Easiest, Free)

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) and sign up
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your repo
5. Add environment variables:
   - `SLACK_BOT_TOKEN`
   - `SLACK_APP_TOKEN`
   - `SPOTTED_CHANNEL_ID`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
6. Deploy! Railway auto-detects the `Procfile` and runs your bot

**Free tier:** 500 hours/month (plenty for a small bot)

### Option 2: Render (Also Free)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) and sign up
3. Click **New** → **Background Worker**
4. Connect your GitHub repo
5. Render auto-detects `render.yaml`
6. Add your environment variables in the dashboard
7. Deploy!

**Free tier:** Runs 24/7 with some limitations

### Option 3: Heroku

1. Push to GitHub
2. Create a Heroku app: [heroku.com](https://heroku.com)
3. Connect your GitHub repo
4. Set Config Vars (environment variables)
5. Enable the worker dyno (not web dyno)
6. Deploy!

**Note:** Heroku removed free tier, costs $5-7/month

### Option 4: DigitalOcean/AWS/Any VPS

```bash
# SSH into your server
git clone <your-repo>
cd Spotted_Leaderboard
pip install -r requirements.txt

# Create .env file with your tokens
nano .env

# Run in background
nohup python bot.py > bot.log 2>&1 &

# Or use screen/tmux to keep it running
screen -S bot
python bot.py
# Ctrl+A then D to detach
```

### Quick Deploy to Railway (Recommended)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Add environment variables
railway variables set SLACK_BOT_TOKEN=xoxb-...
railway variables set SLACK_APP_TOKEN=xapp-...
railway variables set SPOTTED_CHANNEL_ID=C...
railway variables set SUPABASE_URL=https://...
railway variables set SUPABASE_KEY=eyJh...
```

## Troubleshooting

- **Bot not responding?** Make sure it's invited to the channel and Socket Mode is enabled
- **Missing permissions?** Double-check all OAuth scopes are added and reinstall the app
- **Wrong channel?** Verify the `SPOTTED_CHANNEL_ID` matches your target channel
- **Some spots missed?** Bot waits 2 seconds and retries if files aren't immediately attached
- **"No files detected" in logs?** Normal - the bot will retry after 2 seconds to fetch files

## Rules

- You can't spot yourself (self-mentions are ignored)
- Can tag multiple people in one message - all assumed to be in the photo(s)
- Spotter gets +1 per person tagged
- Each tagged person gets -1
- Only works in the designated channel
- Must include at least one photo AND at least one mention

