from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from app.database.connection import database_pool
from app.core.config import settings
from app.core.auth import verify_api_key

router = APIRouter()


@router.get("/", dependencies=[Depends(verify_api_key)])
async def get_venues(
    search: Optional[str] = Query(None, description="Search by name or city"),
    state: Optional[str] = Query(None, description="Filter by state")
):
    """Get all venues with optional filters."""
    where_clauses = []
    params = []
    param_count = 0
    
    if search:
        param_count += 1
        where_clauses.append(f"(name ILIKE ${param_count} OR city ILIKE ${param_count})")
        params.append(f"%{search}%")
    
    if state:
        param_count += 1
        where_clauses.append(f"state = ${param_count}")
        params.append(state)
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
        SELECT 
            id,
            name,
            city,
            state,
            capacity,
            surface,
            opened_year,
            latitude,
            longitude
        FROM venue
        WHERE {where_clause}
        ORDER BY name
    """
    
    venues = await database_pool.fetch(query, *params)
    
    return {
        "venues": venues,
        "total": len(venues)
    }


@router.get("/{venue_id}", dependencies=[Depends(verify_api_key)])
async def get_venue(venue_id: str):
    """Get detailed information for a specific venue."""
    query = """
        SELECT *
        FROM venue
        WHERE id = $1
    """
    
    venue = await database_pool.fetchrow(query, venue_id)
    
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    return venue


@router.get("/{venue_id}/matches", dependencies=[Depends(verify_api_key)])
async def get_venue_matches(
    venue_id: str,
    season: Optional[int] = Query(None, description="Filter by season"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(50, ge=1, le=200, description="Number of items per page")
):
    """Get all matches played at a specific venue."""
    offset = (page - 1) * page_size
    
    # Verify venue exists
    venue_query = "SELECT name FROM venue WHERE id = $1"
    venue = await database_pool.fetchrow(venue_query, venue_id)
    
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    params = [venue_id]
    season_filter = ""
    
    if season:
        season_filter = "AND mr.season_id = $2"
        params.append(season)
    
    # Count query
    count_query = f"""
        SELECT COUNT(*)
        FROM match_registry mr
        WHERE mr.venue_id = $1
        {season_filter}
    """
    total = await database_pool.fetchval(count_query, *params)
    
    # Matches query
    query = f"""
        SELECT 
            mr.id,
            mr.fbref_match_id,
            mr.match_date,
            mr.season_id,
            mr.home_goals,
            mr.away_goals,
            ht.name as home_team,
            at.name as away_team,
            mr.attendance,
            mr.type
        FROM match_registry mr
        JOIN team ht ON mr.home_teams_id = ht.id
        JOIN team at ON mr.away_teams_id = at.id
        WHERE mr.venue_id = $1
        {season_filter}
        ORDER BY mr.match_date DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([page_size, offset])
    
    matches = await database_pool.fetch(query, *params)
    
    return {
        "venue": venue,
        "matches": matches,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{venue_id}/stats", dependencies=[Depends(verify_api_key)])
async def get_venue_stats(venue_id: str):
    """Get statistics for matches played at a venue."""
    # Verify venue exists
    venue_query = "SELECT name, city, state FROM venue WHERE id = $1"
    venue = await database_pool.fetchrow(venue_query, venue_id)
    
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    stats_query = """
        SELECT 
            COUNT(*) as total_matches,
            AVG(attendance)::numeric(10,0) as avg_attendance,
            MAX(attendance) as max_attendance,
            MIN(attendance) as min_attendance,
            AVG(home_goals + away_goals)::numeric(10,2) as avg_goals_per_match,
            COUNT(DISTINCT season_id) as seasons,
            MIN(match_date) as first_match,
            MAX(match_date) as last_match
        FROM match_registry
        WHERE venue_id = $1
    """
    
    stats = await database_pool.fetchrow(stats_query, venue_id)
    
    # Get home team advantage stats
    home_advantage_query = """
        SELECT 
            COUNT(CASE WHEN home_goals > away_goals THEN 1 END) as home_wins,
            COUNT(CASE WHEN home_goals = away_goals THEN 1 END) as draws,
            COUNT(CASE WHEN home_goals < away_goals THEN 1 END) as away_wins,
            AVG(home_goals)::numeric(10,2) as avg_home_goals,
            AVG(away_goals)::numeric(10,2) as avg_away_goals
        FROM match_registry
        WHERE venue_id = $1
    """
    
    home_advantage = await database_pool.fetchrow(home_advantage_query, venue_id)
    
    return {
        "venue": venue,
        "statistics": stats,
        "home_advantage": home_advantage
    }