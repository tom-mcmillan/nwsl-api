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
    description="""
National Women's Soccer League API

Access comprehensive NWSL data including teams, players, matches, and detailed statistics.

**Authentication**  
All endpoints require an API key. For demo access, use:
- Header: `X-API-Key`
- Value: `nwsl-demo-key-2024`

**Get Your API Key**  
Register at: https://api.nwsldata.com/register

**Available Data**
- **Teams**: 16 NWSL teams with complete profiles and statistics
- **Players**: 500+ player profiles with positions, nationalities, and career stats  
- **Matches**: 1,500+ matches with scores, lineups, and detailed events
- **Match Events**: 9,000+ goals, cards, and substitutions
- **Player Stats**: Career and season statistics, leaderboards
- **Venues**: Stadium information with capacity and location details

**Features**
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

**Response Formats**
All responses are in JSON format with consistent structure:
- Success responses include the requested data
- Error responses include status code and detail message
- List endpoints include pagination metadata

**Example Request**
```bash
curl -H "X-API-Key: nwsl-demo-key-2024" https://api.nwsldata.com/api/v1/teams/
```
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