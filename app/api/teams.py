from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List
from app.database.connection import database_pool
from app.core.config import settings
from app.core.auth import verify_api_key

router = APIRouter()


@router.get("/", dependencies=[Depends(verify_api_key)])
async def get_teams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Number of items per page"),
    search: Optional[str] = Query(None, description="Search teams by name or city")
):
    """
    Get all NWSL teams with pagination.
    
    Returns team information including name, city, venue, etc.
    """
    offset = (page - 1) * page_size
    
    where_clause = ""
    params = []
    param_count = 0
    
    if search:
        param_count += 1
        where_clause = f"WHERE team_name ILIKE ${param_count} OR team_name_long ILIKE ${param_count}"
        params.append(f"%{search}%")
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM team {where_clause}"
    total = await database_pool.fetchval(count_query, *params)
    
    # Get teams
    query = f"""
        SELECT id, team_id, team_name, team_name_long, 
               active_2024, active_2025, created_at
        FROM team
        {where_clause}
        ORDER BY team_name
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([page_size, offset])
    
    teams = await database_pool.fetch(query, *params)
    
    return {
        "teams": teams,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{team_id}", dependencies=[Depends(verify_api_key)])
async def get_team(team_id: str):
    """Get detailed information for a specific team."""
    query = """
        SELECT id, team_id, team_name, team_name_long,
               active_2013, active_2014, active_2015, active_2016, active_2017,
               active_2018, active_2019, active_2020, active_2021, active_2022,
               active_2023, active_2024, active_2025, created_at
        FROM team
        WHERE id = $1 OR team_id = $1
    """
    
    team = await database_pool.fetchrow(query, team_id)
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return team


@router.get("/{team_id}/players", dependencies=[Depends(verify_api_key)])
async def get_team_players(
    team_id: str,
    season: Optional[int] = Query(None, description="Filter by season")
):
    """Get all players for a specific team."""
    # First verify team exists
    team_query = "SELECT team_name FROM team WHERE id = $1 OR team_id = $1"
    team = await database_pool.fetchrow(team_query, team_id)
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get players from match lineups
    params = [team_id]
    season_filter = ""
    
    if season:
        season_filter = "AND ml.season_id = $2"
        params.append(season)
    
    query = f"""
        SELECT DISTINCT 
            p.id,
            p.first_name,
            p.last_name,
            p.display_name,
            p.position,
            p.nationality,
            p.birth_date,
            ml.season_id as season
        FROM match_lineup ml
        JOIN player p ON ml.player_id = p.id
        WHERE ml.team_id = $1
        {season_filter}
        ORDER BY p.last_name, p.first_name
    """
    
    players = await database_pool.fetch(query, *params)
    
    return {
        "team": team,
        "players": players,
        "count": len(players)
    }


@router.get("/{team_id}/matches", dependencies=[Depends(verify_api_key)])
async def get_team_matches(
    team_id: str,
    season: Optional[int] = Query(None, description="Filter by season"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Number of items per page")
):
    """Get all matches for a specific team."""
    offset = (page - 1) * page_size
    
    params = [team_id]
    season_filter = ""
    
    if season:
        season_filter = "AND mr.season_id = $2"
        params.append(season)
    
    # Count query
    count_query = f"""
        SELECT COUNT(*)
        FROM match_registry mr
        WHERE (mr.home_teams_id = $1 OR mr.away_teams_id = $1)
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
            mr.home_teams_id,
            mr.away_teams_id,
            ht.team_name as home_team_name,
            at.team_name as away_team_name,
            v.name as venue_name,
            mr.attendance,
            mr.type,
            CASE 
                WHEN mr.home_teams_id = $1 THEN 'home'
                ELSE 'away'
            END as team_side,
            CASE
                WHEN mr.home_teams_id = $1 AND mr.home_goals > mr.away_goals THEN 'W'
                WHEN mr.away_teams_id = $1 AND mr.away_goals > mr.home_goals THEN 'W'
                WHEN mr.home_goals = mr.away_goals THEN 'D'
                ELSE 'L'
            END as result
        FROM match_registry mr
        LEFT JOIN team ht ON mr.home_teams_id = ht.id
        LEFT JOIN team at ON mr.away_teams_id = at.id
        LEFT JOIN venue v ON mr.venue_id = v.id
        WHERE (mr.home_teams_id = $1 OR mr.away_teams_id = $1)
        {season_filter}
        ORDER BY mr.match_date DESC
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


@router.get("/{team_id}/stats", dependencies=[Depends(verify_api_key)])
async def get_team_stats(
    team_id: str,
    season: Optional[int] = Query(None, description="Filter by season")
):
    """Get aggregated statistics for a team."""
    params = [team_id]
    season_filter = ""
    
    if season:
        season_filter = "AND season_id = $2"
        params.append(season)
    
    query = f"""
        SELECT 
            COUNT(*) as matches_played,
            SUM(goals_for) as total_goals_for,
            SUM(goals_against) as total_goals_against,
            SUM(CASE WHEN outcome = 'Win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'Draw' THEN 1 ELSE 0 END) as draws,
            SUM(CASE WHEN outcome = 'Loss' THEN 1 ELSE 0 END) as losses,
            SUM(points) as total_points,
            AVG(total_passes_attempted)::numeric(10,2) as avg_passes_attempted,
            AVG(pass_completion_pct)::numeric(10,2) as avg_pass_completion,
            AVG(total_shots)::numeric(10,2) as avg_shots,
            AVG(shots_on_target)::numeric(10,2) as avg_shots_on_target,
            AVG(total_xg)::numeric(10,2) as avg_xg,
            SUM(yellow_cards) as total_yellow_cards,
            SUM(red_cards) as total_red_cards
        FROM match_team_summary
        WHERE team_id = $1
        {season_filter}
    """
    
    stats = await database_pool.fetchrow(query, *params)
    
    if not stats or stats['matches_played'] == 0:
        raise HTTPException(status_code=404, detail="No statistics found for this team")
    
    return stats