from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from datetime import date
from app.database.connection import database_pool
from app.core.config import settings
from app.core.auth import verify_api_key

router = APIRouter()


@router.get("/", dependencies=[Depends(verify_api_key)])
async def get_matches(
    season: Optional[int] = Query(None, description="Filter by season"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    start_date: Optional[date] = Query(None, description="Filter matches after this date"),
    end_date: Optional[date] = Query(None, description="Filter matches before this date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE)
):
    """Get all matches with filters and pagination."""
    offset = (page - 1) * page_size
    
    where_clauses = []
    params = []
    param_count = 0
    
    if season:
        param_count += 1
        where_clauses.append(f"mr.season_id = ${param_count}")
        params.append(season)
    
    if team_id:
        param_count += 1
        where_clauses.append(f"(mr.home_teams_id = ${param_count} OR mr.away_teams_id = ${param_count})")
        params.append(team_id)
    
    if start_date:
        param_count += 1
        where_clauses.append(f"mr.match_date >= ${param_count}")
        params.append(start_date)
    
    if end_date:
        param_count += 1
        where_clauses.append(f"mr.match_date <= ${param_count}")
        params.append(end_date)
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Count query
    count_query = f"SELECT COUNT(*) FROM match_registry mr WHERE {where_clause}"
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
            ht.id as home_team_id,
            ht.name as home_team_name,
            at.id as away_team_id,
            at.name as away_team_name,
            v.name as venue_name,
            v.city as venue_city,
            mr.attendance,
            mr.type,
            mr.round
        FROM match_registry mr
        LEFT JOIN team ht ON mr.home_teams_id = ht.id
        LEFT JOIN team at ON mr.away_teams_id = at.id
        LEFT JOIN venue v ON mr.venue_id = v.id
        WHERE {where_clause}
        ORDER BY mr.match_date DESC, mr.time DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([page_size, offset])
    
    matches = await database_pool.fetch(query, *params)
    
    return {
        "matches": matches,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{match_id}", dependencies=[Depends(verify_api_key)])
async def get_match(match_id: str):
    """Get detailed information for a specific match."""
    query = """
        SELECT 
            mr.*,
            ht.name as home_team_name,
            at.name as away_team_name,
            v.name as venue_name,
            v.city as venue_city,
            v.state as venue_state
        FROM match_registry mr
        LEFT JOIN team ht ON mr.home_teams_id = ht.id
        LEFT JOIN team at ON mr.away_teams_id = at.id
        LEFT JOIN venue v ON mr.venue_id = v.id
        WHERE mr.id = $1 OR mr.fbref_match_id = $1
    """
    
    match = await database_pool.fetchrow(query, match_id)
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return match


@router.get("/{match_id}/lineups", dependencies=[Depends(verify_api_key)])
async def get_match_lineups(match_id: str):
    """Get lineups for both teams in a match."""
    # First get the match to get team IDs
    match_query = """
        SELECT id, home_teams_id, away_teams_id, match_date
        FROM match_registry
        WHERE id = $1 OR fbref_match_id = $1
    """
    match = await database_pool.fetchrow(match_query, match_id)
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get lineups
    lineup_query = """
        SELECT 
            ml.id,
            ml.player_id,
            p.first_name,
            p.last_name,
            p.display_name,
            ml.position,
            ml.shirt_number,
            ml.minutes_played,
            ml.started,
            ml.subbed_on,
            ml.subbed_off,
            ml.team_id,
            t.name as team_name
        FROM match_lineup ml
        JOIN player p ON ml.player_id = p.id
        JOIN team t ON ml.team_id = t.id
        WHERE ml.match_uuid = $1
        ORDER BY t.name, ml.started DESC, ml.shirt_number
    """
    
    lineups = await database_pool.fetch(lineup_query, match['id'])
    
    # Group by team
    home_lineup = [l for l in lineups if l['team_id'] == match['home_teams_id']]
    away_lineup = [l for l in lineups if l['team_id'] == match['away_teams_id']]
    
    return {
        "match_id": match['id'],
        "match_date": match['match_date'],
        "home_lineup": home_lineup,
        "away_lineup": away_lineup
    }


@router.get("/{match_id}/events", dependencies=[Depends(verify_api_key)])
async def get_match_events(match_id: str):
    """Get all events (goals, cards, substitutions) for a match."""
    # First verify match exists
    match_query = "SELECT id FROM match_registry WHERE id = $1 OR fbref_match_id = $1"
    match = await database_pool.fetchrow(match_query, match_id)
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    query = """
        SELECT 
            me.id,
            me.minute,
            me.stoppage_time,
            me.type,
            me.detail,
            me.score_home,
            me.score_away,
            t.name as team_name,
            gp.display_name as goal_player,
            ap.display_name as assist_player,
            cp.display_name as card_player,
            sip.display_name as substitution_in_player,
            sop.display_name as substitution_out_player
        FROM match_event me
        LEFT JOIN team t ON me.team_uuid = t.id
        LEFT JOIN player gp ON me.goal_player_id = gp.id
        LEFT JOIN player ap ON me.assist_player_id = ap.id
        LEFT JOIN player cp ON me.card_player_id = cp.id
        LEFT JOIN player sip ON me.substitution_in_player_id = sip.id
        LEFT JOIN player sop ON me.substitution_out_player_id = sop.id
        WHERE me.match_uuid = $1
        ORDER BY me.minute, me.stoppage_time
    """
    
    events = await database_pool.fetch(query, match['id'])
    
    return {
        "match_id": match['id'],
        "events": events,
        "total_events": len(events)
    }


@router.get("/{match_id}/stats", dependencies=[Depends(verify_api_key)])
async def get_match_stats(match_id: str):
    """Get team statistics for a match."""
    # Verify match exists
    match_query = "SELECT id FROM match_registry WHERE id = $1 OR fbref_match_id = $1"
    match = await database_pool.fetchrow(match_query, match_id)
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    query = """
        SELECT 
            mts.*,
            t.name as team_name,
            t.city as team_city
        FROM match_team_summary mts
        JOIN team t ON mts.team_id = t.id
        WHERE mts.match_uuid = $1
        ORDER BY mts.is_home DESC
    """
    
    stats = await database_pool.fetch(query, match['id'])
    
    if not stats:
        raise HTTPException(status_code=404, detail="No statistics found for this match")
    
    return {
        "match_id": match['id'],
        "home_stats": stats[0] if stats and stats[0]['is_home'] else None,
        "away_stats": stats[1] if len(stats) > 1 else stats[0] if stats and not stats[0]['is_home'] else None
    }