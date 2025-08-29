from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from app.database.connection import database_pool
from app.core.config import settings
from app.core.auth import verify_api_key

router = APIRouter()


@router.get("/leaderboard/goals", dependencies=[Depends(verify_api_key)])
async def get_goal_leaders(
    season: Optional[int] = Query(None, description="Filter by season"),
    limit: int = Query(10, ge=1, le=100, description="Number of players to return")
):
    """Get top goal scorers."""
    params = []
    season_filter = ""
    
    if season:
        season_filter = "WHERE season_id = $1"
        params.append(season)
    
    query = f"""
        SELECT 
            goal_player_id as player_id,
            p.first_name,
            p.last_name,
            p.display_name,
            COUNT(*) as goals,
            COUNT(DISTINCT match_id) as matches
        FROM match_event me
        JOIN player p ON me.goal_player_id = p.id
        WHERE type = 'goal' AND goal_player_id IS NOT NULL
        {season_filter if params else ''}
        {'AND' if params else 'WHERE'} me.season_id = ${len(params) + 1 if not params else 2}
        GROUP BY goal_player_id, p.first_name, p.last_name, p.display_name
        ORDER BY goals DESC
        LIMIT ${len(params) + 1 if params else 1}
    """
    
    if not season:
        # Default to current season if not specified
        params.append(2025)
    params.append(limit)
    
    leaders = await database_pool.fetch(query, *params)
    
    return {
        "season": season if season else "2025",
        "leaderboard": leaders
    }


@router.get("/leaderboard/assists", dependencies=[Depends(verify_api_key)])
async def get_assist_leaders(
    season: Optional[int] = Query(None, description="Filter by season"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return")
):
    """Get top assist providers."""
    params = []
    
    if season:
        params.append(season)
        season_filter = "AND season_id = $1"
    else:
        season_filter = ""
    
    query = f"""
        SELECT 
            assist_player_id as player_id,
            p.first_name,
            p.last_name,
            p.display_name,
            COUNT(*) as assists
        FROM match_event me
        JOIN player p ON me.assist_player_id = p.id
        WHERE assist_player_id IS NOT NULL
        {season_filter}
        GROUP BY assist_player_id, p.first_name, p.last_name, p.display_name
        ORDER BY assists DESC
        LIMIT ${len(params) + 1}
    """
    params.append(limit)
    
    leaders = await database_pool.fetch(query, *params)
    
    return {
        "season": season if season else "all",
        "leaderboard": leaders
    }


@router.get("/leaderboard/clean-sheets", dependencies=[Depends(verify_api_key)])
async def get_clean_sheet_leaders(
    season: Optional[int] = Query(None, description="Filter by season"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return")
):
    """Get goalkeepers with most clean sheets."""
    params = []
    season_filter = ""
    
    if season:
        season_filter = "WHERE mg.season_id = $1"
        params.append(season)
    
    query = f"""
        SELECT 
            mg.player_id,
            p.first_name,
            p.last_name,
            p.display_name,
            COUNT(CASE WHEN mg.goals_against = 0 THEN 1 END) as clean_sheets,
            COUNT(*) as matches_played,
            SUM(mg.saves) as total_saves,
            AVG(mg.save_pct)::numeric(10,1) as avg_save_pct
        FROM match_goalkeeper mg
        JOIN player p ON mg.player_id = p.id
        {season_filter}
        GROUP BY mg.player_id, p.first_name, p.last_name, p.display_name
        HAVING COUNT(*) >= 5
        ORDER BY clean_sheets DESC, matches_played DESC
        LIMIT ${len(params) + 1}
    """
    params.append(limit)
    
    leaders = await database_pool.fetch(query, *params)
    
    return {
        "season": season if season else "all",
        "leaderboard": leaders
    }


@router.get("/team/{team_id}/season/{season}", dependencies=[Depends(verify_api_key)])
async def get_team_season_stats(team_id: str, season: int):
    """Get comprehensive team statistics for a specific season."""
    
    # Get overall season stats
    overall_query = """
        SELECT 
            COUNT(*) as matches_played,
            SUM(CASE WHEN outcome = 'Win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'Draw' THEN 1 ELSE 0 END) as draws,
            SUM(CASE WHEN outcome = 'Loss' THEN 1 ELSE 0 END) as losses,
            SUM(goals_for) as goals_for,
            SUM(goals_against) as goals_against,
            SUM(points) as points,
            AVG(total_passes_attempted)::numeric(10,1) as avg_passes,
            AVG(pass_completion_pct)::numeric(10,1) as avg_pass_completion,
            AVG(total_shots)::numeric(10,1) as avg_shots,
            AVG(total_xg)::numeric(10,2) as avg_xg
        FROM match_team_summary
        WHERE team_id = $1 AND season_id = $2
    """
    
    overall = await database_pool.fetchrow(overall_query, team_id, season)
    
    if not overall or overall['matches_played'] == 0:
        raise HTTPException(status_code=404, detail="No data found for this team/season")
    
    # Get home/away splits
    home_away_query = """
        SELECT 
            is_home,
            COUNT(*) as matches,
            SUM(CASE WHEN outcome = 'Win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'Draw' THEN 1 ELSE 0 END) as draws,
            SUM(CASE WHEN outcome = 'Loss' THEN 1 ELSE 0 END) as losses,
            SUM(goals_for) as goals_for,
            SUM(goals_against) as goals_against
        FROM match_team_summary
        WHERE team_id = $1 AND season_id = $2
        GROUP BY is_home
    """
    
    home_away = await database_pool.fetch(home_away_query, team_id, season)
    
    # Get top scorers for the team
    top_scorers_query = """
        SELECT 
            p.id,
            p.display_name,
            COUNT(*) as goals
        FROM match_event me
        JOIN player p ON me.goal_player_id = p.id
        WHERE me.team_uuid = $1 AND me.season_id = $2 AND me.type = 'goal'
        GROUP BY p.id, p.display_name
        ORDER BY goals DESC
        LIMIT 5
    """
    
    top_scorers = await database_pool.fetch(top_scorers_query, team_id, season)
    
    return {
        "team_id": team_id,
        "season": season,
        "overall": overall,
        "home_away_splits": home_away,
        "top_scorers": top_scorers
    }


@router.get("/player/{player_id}/career", dependencies=[Depends(verify_api_key)])
async def get_player_career_stats(player_id: str):
    """Get career statistics for a player across all seasons."""
    
    # Basic career stats
    career_query = """
        SELECT 
            COUNT(DISTINCT ml.match_id) as total_matches,
            COUNT(DISTINCT ml.season_id) as seasons_played,
            MIN(ml.season_id) as first_season,
            MAX(ml.season_id) as last_season,
            SUM(ml.minutes_played) as total_minutes,
            COUNT(DISTINCT ml.team_id) as teams_played_for
        FROM match_lineup ml
        WHERE ml.player_id = $1
    """
    
    career = await database_pool.fetchrow(career_query, player_id)
    
    if not career or career['total_matches'] == 0:
        raise HTTPException(status_code=404, detail="No career data found for this player")
    
    # Goals and assists
    scoring_query = """
        SELECT 
            COUNT(CASE WHEN goal_player_id = $1 THEN 1 END) as career_goals,
            COUNT(CASE WHEN assist_player_id = $1 THEN 1 END) as career_assists
        FROM match_event
        WHERE goal_player_id = $1 OR assist_player_id = $1
    """
    
    scoring = await database_pool.fetchrow(scoring_query, player_id)
    
    # Season by season breakdown
    season_breakdown_query = """
        SELECT 
            ml.season_id,
            COUNT(DISTINCT ml.match_id) as matches,
            SUM(ml.minutes_played) as minutes,
            COUNT(CASE WHEN me.goal_player_id = $1 THEN 1 END) as goals,
            COUNT(CASE WHEN me.assist_player_id = $1 THEN 1 END) as assists
        FROM match_lineup ml
        LEFT JOIN match_event me ON ml.match_uuid = me.match_uuid 
            AND ml.season_id = me.season_id
            AND (me.goal_player_id = $1 OR me.assist_player_id = $1)
        WHERE ml.player_id = $1
        GROUP BY ml.season_id
        ORDER BY ml.season_id DESC
    """
    
    seasons = await database_pool.fetch(season_breakdown_query, player_id)
    
    return {
        "player_id": player_id,
        "career_totals": {
            **career,
            **scoring
        },
        "season_breakdown": seasons
    }