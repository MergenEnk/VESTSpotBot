# API Integration Guide

Your bot now exposes REST API endpoints that any webapp can call to get leaderboard data.

## Running Bot with API

```bash
python main.py
```

This runs both the Slack bot AND the API server together.

## API Endpoints

### GET `/api/leaderboard`
Returns full leaderboard sorted by score (highest first).

**Response:**
```json
{
  "leaderboard": [
    {"user_id": "U123456", "score": 5},
    {"user_id": "U789012", "score": -2}
  ]
}
```

### GET `/api/score/<user_id>`
Returns specific user's score.

**Response:**
```json
{
  "user_id": "U123456",
  "score": 5
}
```

### GET `/api/stats`
Returns overall statistics.

**Response:**
```json
{
  "total_players": 10,
  "total_spots": 25,
  "top_spotter": {"user_id": "U123456", "score": 8},
  "most_spotted": {"user_id": "U789012", "score": -5}
}
```

## Using in Your Webapp

### React/Next.js Example

```javascript
// In your separate webapp repo
const API_URL = 'https://your-bot.railway.app/api';

export default function Leaderboard() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch(`${API_URL}/leaderboard`)
      .then(res => res.json())
      .then(data => setData(data.leaderboard));
  }, []);

  return (
    <div>
      {data.map((item, i) => (
        <div key={item.user_id}>
          {i + 1}. {item.user_id}: {item.score} points
        </div>
      ))}
    </div>
  );
}
```

### Vanilla JavaScript Example

See `example_webapp.html` for a complete working example!

### Node.js Backend Example

```javascript
const fetch = require('node-fetch');

async function getLeaderboard() {
  const response = await fetch('https://your-bot.railway.app/api/leaderboard');
  const data = await response.json();
  return data.leaderboard;
}
```

## Deployment

When you deploy to Railway/Render:

1. The bot will automatically expose the API
2. Your webapp calls: `https://your-deployment.railway.app/api/leaderboard`
3. No additional configuration needed!

## Testing Locally

1. Start bot: `python main.py`
2. Open `example_webapp.html` in your browser
3. Should see the leaderboard!

Or test with curl:
```bash
curl http://localhost:5000/api/leaderboard
curl http://localhost:5000/api/stats
```

## CORS

The API has CORS enabled, so you can call it from any domain. If you want to restrict it:

```python
# In api.py
CORS(app, origins=['https://your-webapp.com'])
```

