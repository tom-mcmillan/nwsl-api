from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from app.database.connection import database_pool
from app.core.config import settings
from app.core.auth import verify_api_key

router = APIRouter()


@router.get("/", dependencies=[Depends(verify_api_key)])
async def get_events(
    event_type: Optional[str] = Query(None, description="Filter by type (goal, card, substitution)"),
    season: Optional[int] = Query(None, description="Filter by season"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    player_id: Optional[str] = Query(None, description="Filter by player"),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE)
):
    """Get match events with filters."""
    offset = (page - 1) * page_size
    
    where_clauses = []
    params = []
    param_count = 0
    
    if event_type:
        param_count += 1
        where_clauses.append(f"me.type = ${param_count}")
        params.append(event_type)
    
    if season:
        param_count += 1
        where_clauses.append(f"me.season_id = ${param_count}")
        params.append(season)
    
    if team_id:
        param_count += 1
        where_clauses.append(f"me.team_uuid = ${param_count}")
        params.append(team_id)
    
    if player_id:
        param_count += 1
        where_clauses.append(f"(me.goal_player_id = ${param_count} OR me.assist_player_id = ${param_count} OR me.card_player_id = ${param_count} OR me.substitution_in_player_id = ${param_count} OR me.substitution_out_player_id = ${param_count})")
        params.append(player_id)
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Count query
    count_query = f"SELECT COUNT(*) FROM match_event me WHERE {where_clause}"
    total = await database_pool.fetchval(count_query, *params)
    
    # Events query
    query = f"""
        SELECT 
            me.*,
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
        WHERE {where_clause}
        ORDER BY me.match_date DESC, me.minute
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([page_size, offset])
    
    events = await database_pool.fetch(query, *params)
    
    return {
        "events": events,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/goals", dependencies=[Depends(verify_api_key)])
async def get_goals(
    season: Optional[int] = Query(None, description="Filter by season"),
    player_id: Optional[str] = Query(None, description="Filter by scorer"),
    team_id: Optional[str] = Query(None, description="Filter by team")
):
    """Get all goals with optional filters."""
    where_clauses = ["type = 'goal'"]
    params = []
    param_count = 0
    
    if season:
        param_count += 1
        where_clauses.append(f"season_id = ${param_count}")
        params.append(season)
    
    if player_id:
        param_count += 1
        where_clauses.append(f"goal_player_id = ${param_count}")
        params.append(player_id)
    
    if team_id:
        param_count += 1
        where_clauses.append(f"team_uuid = ${param_count}")
        params.append(team_id)
    
    where_clause = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            me.id,
            me.match_date,
            me.minute,
            me.score_home,
            me.score_away,
            p.display_name as scorer,
            ap.display_name as assist_by,
            t.name as team_name,
            me.detail
        FROM match_event me
        LEFT JOIN player p ON me.goal_player_id = p.id
        LEFT JOIN player ap ON me.assist_player_id = ap.id
        LEFT JOIN team t ON me.team_uuid = t.id
        WHERE {where_clause}
        ORDER BY me.match_date DESC, me.minute
    """
    
    goals = await database_pool.fetch(query, *params)
    
    return {
        "goals": goals,
        "total": len(goals)
    }


@router.get("/cards", dependencies=[Depends(verify_api_key)])
async def get_cards(
    card_type: Optional[str] = Query(None, description="yellow or red"),
    season: Optional[int] = Query(None, description="Filter by season"),
    player_id: Optional[str] = Query(None, description="Filter by player")
):
    """Get all cards (yellow/red) with filters."""
    where_clauses = ["(type = 'yellow_card' OR type = 'red_card')"]
    params = []
    param_count = 0
    
    if card_type:
        where_clauses = [f"type = '{card_type}_card'"]
    
    if season:
        param_count += 1
        where_clauses.append(f"season_id = ${param_count}")
        params.append(season)
    
    if player_id:
        param_count += 1
        where_clauses.append(f"card_player_id = ${param_count}")
        params.append(player_id)
    
    where_clause = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            me.id,
            me.match_date,
            me.minute,
            me.type,
            p.display_name as player_name,
            t.name as team_name,
            me.detail
        FROM match_event me
        LEFT JOIN player p ON me.card_player_id = p.id
        LEFT JOIN team t ON me.team_uuid = t.id
        WHERE {where_clause}
        ORDER BY me.match_date DESC, me.minute
    """
    
    cards = await database_pool.fetch(query, *params)
    
    return {
        "cards": cards,
        "total": len(cards)
    }