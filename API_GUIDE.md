# Webapp Integration Guide

Your bot now uses a **hybrid approach**: the webapp fetches data directly from Supabase, while a minimal Flask API provides health checks for deployment platforms.

## Architecture

```
┌─────────────┐
│   Webapp    │──────┐
└─────────────┘      │
                     ├─► Supabase DB (Direct access)
┌─────────────┐      │
│ Slack Bot   │──────┘
└─────────────┘
       │
       ▼
  Flask API (Health check only)
```

## Running Bot

```bash
python main.py
```

This runs:
1. **Slack bot** (processes spots)
2. **Flask API** (health check endpoint only)

## Health Check Endpoint

### GET `/`
Returns bot status for deployment monitoring.

**Response:**
```json
{
  "status": "ok",
  "service": "Spotted Bot",
  "message": "Bot is running. Webapp uses Supabase directly for data."
}
```

## Webapp Setup

Your webapp fetches data **directly from Supabase** (no middleman API needed).

### Example Implementation

See `example_webapp.html` for a complete working example!

**Quick setup:**

```html
<script type="module">
  // Your Supabase credentials
  const SUPABASE_URL = 'https://xxxxx.supabase.co';
  const SUPABASE_ANON_KEY = 'your-anon-key';  // Safe to expose with RLS
  
  // Import Supabase client
  import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
  
  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  
  // Fetch leaderboard
  const { data, error } = await supabase
    .from('scores')
    .select('user_id, user_name, score')
    .order('score', { ascending: false })
    .limit(100);
</script>
```

### React/Next.js Example

```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

export default function Leaderboard() {
  const [data, setData] = useState([]);

  useEffect(() => {
    async function fetchLeaderboard() {
      const { data, error } = await supabase
        .from('scores')
        .select('user_id, user_name, score')
        .order('score', { ascending: false })
        .limit(100);
      
      if (!error) setData(data);
    }
    
    fetchLeaderboard();
  }, []);

  return (
    <div>
      {data.map((item, i) => (
        <div key={item.user_id}>
          {i + 1}. {item.user_name}: {item.score} points
        </div>
      ))}
    </div>
  );
}
```

### Real-time Updates (Bonus!)

Supabase supports real-time subscriptions:

```javascript
// Subscribe to changes
supabase
  .channel('scores-channel')
  .on('postgres_changes', { 
    event: '*', 
    schema: 'public', 
    table: 'scores' 
  }, (payload) => {
    console.log('Score updated!', payload);
    fetchLeaderboard(); // Refresh
  })
  .subscribe();
```

## Security: Row Level Security (RLS)

Enable RLS in Supabase to control access:

```sql
-- Enable RLS on scores table
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Public read access"
ON scores FOR SELECT
TO anon
USING (true);

-- Only service role can write (your bot)
CREATE POLICY "Service role can write"
ON scores FOR ALL
TO service_role
USING (true);
```

**Important:** Use `SUPABASE_ANON_KEY` in your webapp (read-only), and `SUPABASE_SERVICE_KEY` in your bot (write access).

## Deployment

### Bot Deployment
1. Deploy bot to Railway/Render/Heroku
2. Set environment variables (including `SUPABASE_KEY` = service role key)
3. Health check: `https://your-bot.railway.app/` should return `{"status": "ok"}`

### Webapp Deployment
1. Deploy webapp anywhere (Vercel, Netlify, etc.)
2. Set environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY` (not service key!)
3. Webapp fetches directly from Supabase

## Benefits of This Approach

✅ **Simpler architecture** - No API middleman  
✅ **Real-time updates** - Supabase subscriptions  
✅ **Better performance** - Direct DB access  
✅ **Secure** - RLS controls access  
✅ **Scalable** - Supabase handles load  
✅ **Less code** - No API routes to maintain

## Testing Locally

1. **Start bot:**
   ```bash
   python main.py
   ```

2. **Test health check:**
   ```bash
   curl http://localhost:5000/
   ```

3. **Test webapp:**
   - Update `example_webapp.html` with your Supabase credentials
   - Open in browser
   - Should see leaderboard!

## Supabase Dashboard

Access your data at: `https://app.supabase.com/project/YOUR_PROJECT_ID/editor`

- View/edit scores manually
- Run SQL queries
- Monitor API usage
- Check logs

## Troubleshooting

### "Cannot connect to Supabase"
- Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Verify Supabase project is running
- Check browser console for detailed error

### "Empty leaderboard"
- Check if table `scores` exists
- Verify bot has written some data
- Check RLS policies allow read access

### "403 Forbidden"
- RLS is blocking access
- Make sure you have a public read policy
- Use anon key, not service key in webapp

## Migration from Old API

If you were using the old `/api/leaderboard` endpoints:

**Before:**
```javascript
fetch('https://your-bot.railway.app/api/leaderboard')
```

**After:**
```javascript
supabase.from('scores').select('*').order('score', { ascending: false })
```

The Flask API still exists for health checks, but data routes were removed (simpler!).
