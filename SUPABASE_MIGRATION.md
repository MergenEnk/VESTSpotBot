# Migrating to Supabase

This guide walks you through migrating from SQLite to Supabase for persistent cloud storage.

## Step 1: Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/sign in
2. Click "New Project"
3. Choose an organization and project name
4. Set a database password (save this!)
5. Select a region close to your deployment
6. Wait for the project to be created (~2 minutes)

## Step 2: Set Up the Database Table

1. In your Supabase project dashboard, go to the **SQL Editor**
2. Open the file `supabase_setup.sql` from this repo
3. Copy all the SQL code and paste it into the Supabase SQL Editor
4. Click "Run" to execute the SQL
5. Verify the `scores` table was created by going to **Table Editor** → `scores`

## Step 3: Get Your Supabase Credentials

1. In your Supabase dashboard, go to **Settings** → **API**
2. Copy your **Project URL** (looks like `https://xxxxx.supabase.co`)
3. Copy your **anon/public key** (starts with `eyJh...`)

> **Note:** You can use either the `anon` key or `service_role` key. The `service_role` key has full access and bypasses Row Level Security, which is fine for a bot. The setup SQL includes a permissive RLS policy if you use the `anon` key.

## Step 4: Update Environment Variables

### For Local Development:

Edit your `.env` file (or create one from `config.template`):

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SPOTTED_CHANNEL_ID=C1234567890
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-supabase-key
```

### For Cloud Deployment (Render/Heroku/etc):

Add these environment variables in your hosting platform's dashboard:
- `SUPABASE_URL` = your Supabase project URL
- `SUPABASE_KEY` = your Supabase anon or service role key

## Step 5: (Optional) Migrate Existing Data

If you have existing data in your SQLite database (`spotted.db`) that you want to keep:

```python
# Run this script to export data from SQLite
import sqlite3
import json

conn = sqlite3.connect('spotted.db')
cursor = conn.cursor()
cursor.execute('SELECT user_id, user_name, score FROM scores')
data = cursor.fetchall()
conn.close()

# Print as JSON to import into Supabase
print(json.dumps([{
    'user_id': row[0],
    'user_name': row[1],
    'score': row[2]
} for row in data], indent=2))
```

Then in Supabase:
1. Go to **Table Editor** → `scores`
2. Click **Insert** → **Insert row**
3. Manually insert rows, or use the API/SQL Editor to bulk insert

## Step 6: Test the Connection

Run your bot locally:

```bash
python main.py
```

You should see:
```
✅ Connected to Supabase: https://xxxxx.supabase.co
```

If you see an error, double-check your `SUPABASE_URL` and `SUPABASE_KEY` environment variables.

## Step 7: Deploy

1. Commit your changes:
```bash
git add .
git commit -m "Migrate to Supabase for persistent storage"
git push
```

2. Your cloud deployment will automatically redeploy with the new code
3. Make sure the environment variables are set in your hosting platform

## Verification

Test that everything works:
1. Post a photo with a tagged user in your Slack channel
2. Check the `scores` table in Supabase Table Editor
3. You should see the scores update in real-time!

## Benefits

✅ **Persistent storage** - Data survives redeployments  
✅ **Real-time dashboard** - View data in Supabase UI  
✅ **Scalable** - Handles concurrent requests better than SQLite  
✅ **Backups** - Automatic backups (on paid plans)  
✅ **API access** - Easy to build web dashboards or other integrations

## Troubleshooting

**Error: "SUPABASE_URL and SUPABASE_KEY must be set"**
- Make sure you've set the environment variables correctly
- For local dev, check your `.env` file
- For cloud, check your hosting platform's environment variables

**Connection timeout or slow responses**
- Choose a Supabase region closer to your deployment
- Check your internet connection
- Verify Supabase project is not paused (free tier pauses after 7 days of inactivity)

**RLS policy errors**
- Use the `service_role` key instead of `anon` key, OR
- Make sure you ran the SQL setup script that creates the permissive RLS policy

## Rollback to SQLite (if needed)

If you need to rollback:
1. `git checkout HEAD~1 database.py requirements.txt`
2. Remove `SUPABASE_URL` and `SUPABASE_KEY` from environment variables
3. Redeploy

Note: You'll lose the benefits of persistent storage.

