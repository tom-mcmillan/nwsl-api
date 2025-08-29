from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.database.connection import database_pool
from app.api import teams, players, matches, events, stats, venues, developers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database_pool.connect()
    yield
    # Shutdown
    await database_pool.disconnect()


app = FastAPI(
    title="NWSL API",
    openapi_tags=[
        {
            "name": "Developer Access",
            "description": "Get your API key and manage authentication",
        },
        {
            "name": "Teams",
            "description": "Access team information, rosters, and statistics",
        },
        {
            "name": "Players", 
            "description": "Player profiles, career stats, and match history",
        },
        {
            "name": "Matches",
            "description": "Match schedules, results, lineups, and detailed events",
        },
        {
            "name": "Match Events",
            "description": "Goals, cards, substitutions, and other match events",
        },
        {
            "name": "Statistics",
            "description": "Leaderboards, team stats, and player performance metrics",
        },
        {
            "name": "Venues",
            "description": "Stadium information, capacity, and location details",
        }
    ],
    description="""
# National Women's Soccer League API

Access comprehensive NWSL data including teams, players, matches, and detailed statistics.

## 🚀 Getting Started

### Step 1: Get Your API Key
**[→ Register for Free API Key](https://api.nwsldata.com/register)**

Or use the demo key for testing:
- Header: `X-API-Key`  
- Value: `nwsl-demo-key-2024`

### Step 2: Make Your First Request
Try it right here in the docs! Click any endpoint below, then click "Try it out".

**Quick Start Examples:**

<details>
<summary><b>cURL</b></summary>

```bash
curl -H "X-API-Key: nwsl-demo-key-2024" \\
     https://api.nwsldata.com/api/v1/teams/
```
</details>

<details>
<summary><b>Python</b></summary>

```python
import requests

headers = {"X-API-Key": "nwsl-demo-key-2024"}
response = requests.get("https://api.nwsldata.com/api/v1/teams/", headers=headers)
teams = response.json()
print(f"Found {teams['total']} teams")
```
</details>

<details>
<summary><b>JavaScript</b></summary>

```javascript
const headers = {"X-API-Key": "nwsl-demo-key-2024"};
fetch("https://api.nwsldata.com/api/v1/teams/", {headers})
  .then(res => res.json())
  .then(data => console.log(`Found ${data.total} teams`));
```
</details>

### Step 3: Explore the Data
Click on any section below to see available endpoints. Each endpoint has:
- **Try it out** button for testing
- **Schema** tab showing response structure  
- **Example** responses

## 💡 Common Use Cases

- **Fantasy Sports App**: Track player performance, injuries, and form
- **Match Tracker**: Real-time scores, lineups, and match events
- **Stats Dashboard**: Team and player analytics with historical data
- **News Integration**: Enrich articles with live stats and records
- **Betting Analysis**: Historical performance and head-to-head records

## 📊 Available Data
- **Teams**: 16 NWSL teams with complete profiles and statistics
- **Players**: 500+ player profiles with positions, nationalities, and career stats  
- **Matches**: 1,500+ matches with scores, lineups, and detailed events
- **Match Events**: 9,000+ goals, cards, and substitutions
- **Player Stats**: Career and season statistics, leaderboards
- **Venues**: Stadium information with capacity and location details

## ⚡ Features
- ✅ RESTful API design with consistent patterns
- ✅ Pagination on all list endpoints (page/page_size parameters)
- ✅ Advanced filtering by season, team, player, date ranges
- ✅ Full-text search capabilities on relevant endpoints
- ✅ Comprehensive match and player statistics
- ✅ Real-time data updates during the season

**Rate Limits**
- Demo Key: 100 requests/hour
- Standard Key: 1,000 requests/hour  
- Premium Key: 10,000 requests/hour

## 📋 Response Formats

**Success Response:**
```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**Error Response:**
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
    """,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(developers.router, tags=["Developer Access"])  # No prefix - at root level
app.include_router(teams.router, prefix=f"{settings.API_V1_STR}/teams", tags=["Teams"])
app.include_router(players.router, prefix=f"{settings.API_V1_STR}/players", tags=["Players"])
app.include_router(matches.router, prefix=f"{settings.API_V1_STR}/matches", tags=["Matches"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/events", tags=["Match Events"])
app.include_router(stats.router, prefix=f"{settings.API_V1_STR}/stats", tags=["Statistics"])
app.include_router(venues.router, prefix=f"{settings.API_V1_STR}/venues", tags=["Venues"])


@app.get("/")
async def root():
    """API root endpoint - returns basic API information"""
    return {
        "name": "NWSL API",
        "version": settings.VERSION,
        "documentation": "https://api.nwsldata.com/docs",
        "redoc": "https://api.nwsldata.com/redoc",
        "registration": "https://api.nwsldata.com/register",
        "status": "healthy",
        "demo_key": "nwsl-demo-key-2024"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await database_pool.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )