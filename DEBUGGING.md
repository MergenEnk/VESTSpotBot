# Debugging Guide - Spotted Bot

## Comprehensive Logging Enabled

The bot now has **detailed logging** to help diagnose why some spots might be missed.

## What You'll See in Logs

### When You Post an Image with @mentions:

```
============================================================
🔔 MESSAGE EVENT RECEIVED
============================================================
Channel: C01234567 (Target: C01234567)
User: U01234567
Timestamp: 1234567890.123456
Subtype: None
Text: Hey <@U98765432> look at this!
Has 'files' key: True
Number of files: 1
  File 1: image/jpeg - IMG_1234.jpg
✅ Passed all initial checks, proceeding to file check...
Initial file check: True
✅ Files detected immediately

============================================================
📩 PROCESSING SPOT
============================================================
👤 Spotter: U01234567
✅ Image detected
🏷️  Found mentions: ['U98765432']
✅ Spotted U98765432!
📸 *SPOTTED!* <@U98765432> caught by <@U01234567>!
```

### If Bot Isn't Receiving Messages at All:

**Problem:** You post an image but see NO logs at all (no "MESSAGE EVENT RECEIVED")

**Causes:**
1. Bot not invited to channel
2. Bot not subscribed to `message.channels` event
3. Socket Mode not enabled
4. Wrong `SPOTTED_CHANNEL_ID`

**Fix:**
1. In Slack, type `/invite @YourBotName` in the channel
2. Check Event Subscriptions in Slack App settings
3. Verify Socket Mode is ON
4. Double-check channel ID matches

### If Bot Sees Messages but No Files:

**Logs show:**
```
============================================================
🔔 MESSAGE EVENT RECEIVED
============================================================
Has 'files' key: False
Initial file check: False
⏳ No files detected immediately, waiting 2 seconds and retrying...
🔄 Fetching message history to check for files...
📥 Refetched message, checking for files...
  Has 'files' key: False
❌ Still no files after retry - this is a text-only message
⏭️  No images found, skipping message
```

**Causes:**
1. Bot missing `files:read` permission
2. Files uploaded to thread instead of main channel
3. File is not an image (PDF, video, etc.)
4. Slack API timing issue (rare)

**Fix:**
1. Go to OAuth & Permissions → Add `files:read` scope → Reinstall app
2. Make sure you're posting in the main channel, not a thread
3. Verify file is an image (JPEG, PNG, GIF, etc.)

### If file_shared Events Missing:

**You should see:**
```
📁 file_shared event received: file_id=F1234, user=U1234
```

**If you DON'T see this when uploading images:**

**Causes:**
1. Not subscribed to `file_shared` event
2. App not reinstalled after adding subscription

**Fix:**
1. Go to Event Subscriptions → Subscribe to `file_shared`
2. Click "Reinstall App" in OAuth & Permissions

## Common Scenarios

### Scenario 1: Bot Only Catches SOME Images

**Symptoms:** Bot processes 50% of images, misses others randomly

**Likely Cause:** Timing issue - files not attached when message event fires

**What logs show:**
```
Initial file check: False
⏳ No files detected immediately, waiting 2 seconds and retrying...
```

Then either:
- ✅ `Files detected after retry!` → Should work
- ❌ `Still no files after retry` → Real problem

**Fix:** If you see "Still no files after retry" for actual image posts, there's a permission issue or the files aren't being uploaded correctly.

### Scenario 2: Bot Catches NO Images

**Symptoms:** Bot never processes any image posts

**What to check in logs:**
1. Do you see `🔔 MESSAGE EVENT RECEIVED` at all?
   - NO → Bot not subscribed to events or not in channel
   - YES → Continue to step 2

2. Do you see `Has 'files' key: True`?
   - NO → Missing `files:read` permission
   - YES → Bot should be working

### Scenario 3: Bot Processes Same Image Multiple Times

**Symptoms:** Same spot recorded twice

**What logs show:**
```
⏭️  Message 1234567890.123456 already processed, skipping
```

**If you DON'T see this:** Deduplication not working

**Cause:** Timestamp format issue or cache cleared

**This should NOT happen** with current code.

## Testing Checklist

Use this to verify your bot setup:

### 1. Slack App Configuration

```bash
☐ OAuth Scopes:
  ☐ channels:history
  ☐ channels:read
  ☐ chat:write
  ☐ files:read ← CRITICAL
  ☐ reactions:write
  ☐ users:read

☐ Event Subscriptions:
  ☐ message.channels
  ☐ file_shared

☐ Socket Mode:
  ☐ Enabled
  ☐ App-level token generated

☐ App Installation:
  ☐ Installed to workspace
  ☐ Reinstalled after adding scopes/events
```

### 2. Environment Variables

```bash
☐ SLACK_BOT_TOKEN=xoxb-... (set)
☐ SLACK_APP_TOKEN=xapp-... (set)
☐ SPOTTED_CHANNEL_ID=C... (correct channel)
☐ SUPABASE_URL (set)
☐ SUPABASE_KEY (set)
```

### 3. Bot Status in Channel

```bash
☐ Bot appears in channel member list
☐ Bot shows as "Active" (green dot)
☐ Bot responds to /invite command (or is already member)
```

### 4. Test Messages

Post these and check logs:

```bash
☐ Text only: "Hello"
  Expected: Message received, no files, skipped

☐ Image only (no mentions)
  Expected: Message received, files detected, no mentions, skipped

☐ Image + one @mention: "Look <@USER>"
  Expected: Message received, files detected, spot processed ✅

☐ Image + multiple @mentions
  Expected: All users processed ✅
```

## Emergency Debugging

If nothing works, add this to see RAW events:

In `bot.py`, at the very top of `handle_message`:

```python
print(f"RAW EVENT: {json.dumps(event, indent=2)}")
```

This will show you EXACTLY what Slack is sending.

## Get Help

If you've checked everything above and it still doesn't work:

1. **Copy the logs** from posting one image with @mention
2. **Copy your environment variables** (redact tokens)
3. **Screenshot your Slack App settings:**
   - OAuth & Permissions (scopes)
   - Event Subscriptions
   - Socket Mode
4. Check if other Slack bots in your workspace are working

## Log Emoji Guide

- 🔔 = Message event received
- 📁 = File shared event received
- ✅ = Check passed
- ❌ = Check failed
- ⏭️  = Skipped (intentional)
- ⚠️  = Warning (might be OK)
- 📩 = Processing spot
- 🏷️  = Mentions found
- 👤 = User info
- 🔄 = Retrying
- ⏳ = Waiting

---

**TL;DR:** Deploy the updated code and watch the logs. They'll tell you exactly what's happening.

