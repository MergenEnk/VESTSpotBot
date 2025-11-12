# Hybrid Approach Summary

## What Changed

Simplified the architecture to use **direct Supabase access** for webapp data fetching, keeping only a minimal Flask API for health checks.

## Before (API Middleman)

```
Webapp → Flask API → Supabase DB
          ↑
      Slack Bot
```

- Flask had 4 routes: `/`, `/api/leaderboard`, `/api/score/<user_id>`, `/api/stats`
- Webapp called API endpoints
- More code to maintain

## After (Hybrid Approach)

```
Webapp ──────┐
             ├─► Supabase DB
Slack Bot ───┘
     │
     ▼
Flask API (health check only)
```

- Flask has 1 route: `/` (health check)
- Webapp calls Supabase directly
- Less code, better performance

## Files Modified

### 1. `api.py`
**Before:** 115 lines with full API routes  
**After:** 18 lines with health check only

```python
# Now just this:
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'Spotted Bot',
        'message': 'Bot is running. Webapp uses Supabase directly for data.'
    })
```

### 2. `example_webapp.html`
**Before:** Fetched from Flask API  
**After:** Fetches directly from Supabase using JS client

```javascript
// Now uses Supabase client
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const { data } = await supabase
  .from('scores')
  .select('*')
  .order('score', { ascending: false });
```

### 3. `API_GUIDE.md`
Updated to explain hybrid approach and direct Supabase integration

### 4. `test_setup.py`
Updated to only check for health endpoint (removed API route checks)

### 5. `README.md`
Updated webapp integration section to explain hybrid approach

## Benefits

### ✅ Simpler
- **97 fewer lines** in `api.py` (18 vs 115)
- No API routes to maintain
- Fewer moving parts

### ✅ Faster
- Direct DB access (no API middleman)
- Reduced latency
- Fewer network hops

### ✅ Real-time Capable
- Can add Supabase subscriptions
- Instant updates when scores change
- No polling needed

### ✅ More Secure
- Row Level Security (RLS) at DB level
- Anon key for read-only access
- Service key only for bot writes

### ✅ More Scalable
- Supabase handles all read traffic
- Bot isn't a bottleneck
- CDN caching possible

## What's Still There

### Flask API
Still runs for:
- Health check endpoint (`/`) for deployment platforms
- Keeps bot running in same process

### Bot Functionality
No changes:
- Still processes spots
- Still writes to Supabase
- All robustness features intact

## Setup for Webapp

1. **Get Supabase credentials:**
   - URL: `https://app.supabase.com/project/YOUR_PROJECT/settings/api`
   - Anon key (safe to expose with RLS)

2. **Configure Row Level Security:**
   ```sql
   ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
   
   CREATE POLICY "Public read access"
   ON scores FOR SELECT TO anon USING (true);
   ```

3. **Update webapp:**
   ```javascript
   const SUPABASE_URL = 'your-url';
   const SUPABASE_ANON_KEY = 'your-anon-key';
   ```

4. **Done!** Open `example_webapp.html` to see it work.

## Migration Path

If you had existing webapps using the old API:

**Old code:**
```javascript
fetch('https://your-bot.railway.app/api/leaderboard')
  .then(res => res.json())
  .then(data => setLeaderboard(data.leaderboard));
```

**New code:**
```javascript
const { data } = await supabase
  .from('scores')
  .select('*')
  .order('score', { ascending: false });
setLeaderboard(data);
```

## Questions?

See `API_GUIDE.md` for detailed integration examples, RLS setup, and troubleshooting.

---

**TL;DR:** Removed unnecessary API middleman. Webapp now fetches directly from Supabase. Simpler, faster, more scalable. ✨

