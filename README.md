# NWSL API

A comprehensive REST API for National Women's Soccer League data, built with FastAPI and PostgreSQL.

## 🚀 Features

- **Complete NWSL Data**: Access to teams, players, matches, events, and detailed statistics
- **RESTful Design**: Clean, intuitive endpoints following REST principles
- **API Authentication**: Simple API key authentication for access control
- **Auto Documentation**: Interactive Swagger UI and ReDoc documentation
- **High Performance**: Async operations with connection pooling
- **Comprehensive Filtering**: Search, filter by season, team, player, and more
- **Pagination**: Efficient data retrieval with customizable page sizes

## 📊 Available Data

- **16 NWSL teams** with historical data
- **1,500+ matches** with detailed statistics
- **9,000+ match events** (goals, cards, substitutions)
- **56,000+ player lineups**
- **Complete player statistics** including passing, shooting, defensive metrics
- **Venue information** with attendance data

## 🔑 Authentication

All endpoints require an API key header:
- Header: `X-API-Key`
- Demo value: `nwsl-demo-key-2024`

## 🌐 API Endpoints

### Teams
- `GET /api/v1/teams/` - List all teams
- `GET /api/v1/teams/{team_id}` - Get team details
- `GET /api/v1/teams/{team_id}/players` - Get team roster
- `GET /api/v1/teams/{team_id}/matches` - Get team matches
- `GET /api/v1/teams/{team_id}/stats` - Get team statistics

### Players
- `GET /api/v1/players/` - List all players (with search)
- `GET /api/v1/players/{player_id}` - Get player details
- `GET /api/v1/players/{player_id}/matches` - Get player match history
- `GET /api/v1/players/{player_id}/stats` - Get player statistics
- `GET /api/v1/players/{player_id}/teams` - Get player team history

### Matches
- `GET /api/v1/matches/` - List all matches (with filters)
- `GET /api/v1/matches/{match_id}` - Get match details
- `GET /api/v1/matches/{match_id}/lineups` - Get match lineups
- `GET /api/v1/matches/{match_id}/events` - Get match events
- `GET /api/v1/matches/{match_id}/stats` - Get match statistics

### Events
- `GET /api/v1/events/` - List all events
- `GET /api/v1/events/goals` - Get all goals
- `GET /api/v1/events/cards` - Get all cards

### Statistics
- `GET /api/v1/stats/leaderboard/goals` - Top goal scorers
- `GET /api/v1/stats/leaderboard/assists` - Top assist providers
- `GET /api/v1/stats/leaderboard/clean-sheets` - Top goalkeepers
- `GET /api/v1/stats/team/{team_id}/season/{season}` - Team season stats
- `GET /api/v1/stats/player/{player_id}/career` - Player career stats

### Venues
- `GET /api/v1/venues/` - List all venues
- `GET /api/v1/venues/{venue_id}` - Get venue details
- `GET /api/v1/venues/{venue_id}/matches` - Get venue match history
- `GET /api/v1/venues/{venue_id}/stats` - Get venue statistics

## 🛠 Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database (via Google Cloud SQL)
- Cloud SQL Proxy running on port 5433

### Installation

1. **Clone the repository:**
```bash
git clone <repository>
cd nwsl-api
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up Cloud SQL Proxy:**
```bash
cloud-sql-proxy --port 5433 nwsl-data:us-central1:nwsl-postgres
```

5. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

6. **Run the server:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## 📚 Documentation

- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Landing Page**: http://localhost:8000/

## 💡 Example Queries

### Get teams active in 2024:
```bash
curl -H "X-API-Key: nwsl-demo-key-2024" \
  "http://localhost:8000/api/v1/teams/?search=2024"
```

### Search for players named "Smith":
```bash
curl -H "X-API-Key: nwsl-demo-key-2024" \
  "http://localhost:8000/api/v1/players/?search=Smith"
```

### Get matches for a specific season:
```bash
curl -H "X-API-Key: nwsl-demo-key-2024" \
  "http://localhost:8000/api/v1/matches/?season=2024"
```

### Get top goal scorers:
```bash
curl -H "X-API-Key: nwsl-demo-key-2024" \
  "http://localhost:8000/api/v1/stats/leaderboard/goals?season=2024"
```

## 🏗 Project Structure

```
nwsl-api/
├── app/
│   ├── api/              # API endpoint modules
│   │   ├── teams.py
│   │   ├── players.py
│   │   ├── matches.py
│   │   ├── events.py
│   │   ├── stats.py
│   │   └── venues.py
│   ├── core/             # Core configuration
│   │   ├── config.py
│   │   └── auth.py
│   └── database/         # Database connection
│       └── connection.py
├── main.py               # FastAPI application
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables
```

## 🔒 Security Notes

- The demo API key (`nwsl-demo-key-2024`) is for development only
- In production, implement proper authentication (OAuth2, JWT)
- Use environment variables for sensitive configuration
- Enable HTTPS in production
- Implement rate limiting for production use

## 📈 Performance

- **Connection Pooling**: 10-20 concurrent database connections
- **Async Operations**: Non-blocking I/O for all database queries
- **Pagination**: Default 100 items, max 1000 per request
- **Optimized Queries**: Indexed columns for fast lookups

## 🤝 Contributing

This API is designed to be developer-friendly. Contributions welcome!

## 📝 License

[Your License Here]

## 🆘 Support

For issues or questions about the API, please open an issue in the repository.