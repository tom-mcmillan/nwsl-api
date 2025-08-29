from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from app.database.connection import database_pool
from app.core.config import settings
from app.core.auth import verify_api_key
from datetime import date

router = APIRouter()


@router.get("/", dependencies=[Depends(verify_api_key)])
async def get_players(
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    search: Optional[str] = Query(None, description="Search by name"),
    position: Optional[str] = Query(None, description="Filter by position"),
    nationality: Optional[str] = Query(None, description="Filter by nationality")
):
    """Get all players with pagination and filters."""
    offset = (page - 1) * page_size
    
    where_clauses = []
    params = []
    param_count = 0
    
    if search:
        param_count += 1
        where_clauses.append(f"player_name ILIKE ${param_count}")
        params.append(f"%{search}%")
    
    if position:
        param_count += 1
        where_clauses.append(f"position ILIKE ${param_count}")
        params.append(f"%{position}%")
    
    if nationality:
        param_count += 1
        where_clauses.append(f"nationality ILIKE ${param_count}")
        params.append(f"%{nationality}%")
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Count query
    count_query = f"SELECT COUNT(*) FROM player WHERE {where_clause}"
    total = await database_pool.fetchval(count_query, *params)
    
    # Players query
    query = f"""
        SELECT 
            id,
            player_name,
            position,
            nationality,
            birth_date,
            height_cm,
            nwsl_id,
            created_at
        FROM player
        WHERE {where_clause}
        ORDER BY player_name
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([page_size, offset])
    
    players = await database_pool.fetch(query, *params)
    
    return {
        "players": players,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{player_id}", dependencies=[Depends(verify_api_key)])
async def get_player(player_id: str):
    """Get detailed information for a specific player."""
    query = """
        SELECT 
            id,
            player_name,
            position,
            nationality,
            birth_date,
            height_cm,
            nwsl_id,
            created_at
        FROM player
        WHERE id = $1
    """
    
    player = await database_pool.fetchrow(query, player_id)
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return player


@router.get("/{player_id}/matches", dependencies=[Depends(verify_api_key)])
async def get_player_matches(
    player_id: str,
    season: Optional[int] = Query(None, description="Filter by season"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Get all matches a player has participated in."""
    offset = (page - 1) * page_size
    
    params = [player_id]
    season_filter = ""
    
    if season:
        season_filter = "AND ml.season_id = $2"
        params.append(season)
    
    # Count query
    count_query = f"""
        SELECT COUNT(DISTINCT ml.match_id)
        FROM match_lineup ml
        WHERE ml.player_id = $1
        {season_filter}
    """
    total = await database_pool.fetchval(count_query, *params)
    
    # Matches query
    query = f"""
        SELECT DISTINCT
            mr.id,
            mr.fbref_match_id,
            mr.match_date,
            mr.season_id,
            ml.position,
            ml.minutes_played,
            ml.started,
            ml.subbed_on,
            ml.subbed_off,
            t.name as team_name,
            mr.home_teams_id,
            mr.away_teams_id,
            ht.name as home_team_name,
            at.name as away_team_name,
            mr.home_goals,
            mr.away_goals
        FROM match_lineup ml
        JOIN match_registry mr ON ml.match_uuid = mr.id
        JOIN team t ON ml.team_id = t.id
        LEFT JOIN team ht ON mr.home_teams_id = ht.id
        LEFT JOIN team at ON mr.away_teams_id = at.id
        WHERE ml.player_id = $1
        {season_filter}
        ORDER BY mr.match_date DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([page_size, offset])
    
    matches = await database_pool.fetch(query, *params)
    
    return {
        "player_id": player_id,
        "matches": matches,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{player_id}/stats", dependencies=[Depends(verify_api_key)])
async def get_player_stats(
    player_id: str,
    season: Optional[int] = Query(None, description="Filter by season")
):
    """Get aggregated statistics for a player."""
    params = [player_id]
    season_filter = ""
    
    if season:
        season_filter = "AND ml.season_id = $2"
        params.append(season)
    
    # Get basic stats
    basic_query = f"""
        SELECT 
            COUNT(DISTINCT ml.match_id) as matches_played,
            COUNT(DISTINCT CASE WHEN ml.started THEN ml.match_id END) as matches_started,
            SUM(ml.minutes_played) as total_minutes,
            COUNT(DISTINCT ml.season_id) as seasons_played
        FROM match_lineup ml
        WHERE ml.player_id = $1
        {season_filter}
    """
    
    basic_stats = await database_pool.fetchrow(basic_query, *params)
    
    # Get shooting stats
    shooting_query = f"""
        SELECT 
            COUNT(*) as total_shots,
            COUNT(CASE WHEN outcome = 'Goal' THEN 1 END) as goals,
            COUNT(CASE WHEN outcome = 'Saved' THEN 1 END) as shots_on_target,
            AVG(xg)::numeric(10,3) as avg_xg,
            SUM(xg)::numeric(10,2) as total_xg
        FROM match_shot
        WHERE player_id = $1
        {season_filter.replace('ml.', '')}
    """
    
    shooting_stats = await database_pool.fetchrow(shooting_query, *params)
    
    # Get passing stats (aggregated from match_player_passing)
    passing_query = f"""
        SELECT 
            AVG(passes_cmp)::numeric(10,1) as avg_passes_completed,
            AVG(passes_att)::numeric(10,1) as avg_passes_attempted,
            AVG(passes_cmp_pct)::numeric(10,1) as avg_pass_completion_pct,
            SUM(assists) as total_assists,
            SUM(key_passes) as total_key_passes
        FROM match_player_passing mpp
        JOIN match_lineup ml ON mpp.match_lineup_id = ml.id
        WHERE ml.player_id = $1
        {season_filter}
    """
    
    passing_stats = await database_pool.fetchrow(passing_query, *params)
    
    # Combine all stats
    return {
        "player_id": player_id,
        "season": season if season else "all",
        "matches": basic_stats,
        "shooting": shooting_stats,
        "passing": passing_stats
    }


@router.get("/{player_id}/teams", dependencies=[Depends(verify_api_key)])
async def get_player_teams(player_id: str):
    """Get all teams a player has played for."""
    query = """
        SELECT DISTINCT
            t.id,
            t.name,
            t.city,
            ml.season_id,
            COUNT(DISTINCT ml.match_id) as matches_played
        FROM match_lineup ml
        JOIN team t ON ml.team_id = t.id
        WHERE ml.player_id = $1
        GROUP BY t.id, t.name, t.city, ml.season_id
        ORDER BY ml.season_id DESC, t.name
    """
    
    teams = await database_pool.fetch(query, player_id)
    
    if not teams:
        raise HTTPException(status_code=404, detail="No team history found for this player")
    
    return {
        "player_id": player_id,
        "teams": teams
    }