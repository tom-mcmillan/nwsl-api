from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, PaginatedItems
from app.database.connection import database_pool
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    query = """
        INSERT INTO items (name, description, price, quantity, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
    """
    now = datetime.utcnow()
    
    try:
        row = await database_pool.fetchrow(
            query,
            item.name,
            item.description,
            item.price,
            item.quantity,
            item.is_active,
            now,
            now
        )
        return ItemResponse(**dict(row))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedItems)
async def get_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = None
):
    offset = (page - 1) * per_page
    
    where_clause = ""
    params = [per_page, offset]
    param_count = 2
    
    if search:
        param_count += 1
        where_clause = f"WHERE name ILIKE ${param_count} OR description ILIKE ${param_count}"
        params.append(f"%{search}%")
    
    count_query = f"SELECT COUNT(*) FROM items {where_clause}"
    items_query = f"""
        SELECT * FROM items
        {where_clause}
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
    """
    
    try:
        if search:
            total = await database_pool.fetchval(count_query, f"%{search}%")
        else:
            total = await database_pool.fetchval(count_query)
            
        rows = await database_pool.fetch(items_query, *params)
        items = [ItemResponse(**dict(row)) for row in rows]
        
        total_pages = (total + per_page - 1) // per_page
        
        return PaginatedItems(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    query = "SELECT * FROM items WHERE id = $1"
    
    try:
        row = await database_pool.fetchrow(query, item_id)
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        return ItemResponse(**dict(row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item: ItemUpdate):
    update_data = {k: v for k, v in item.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    query = f"""
        UPDATE items
        SET {set_clause}, updated_at = ${len(update_data) + 2}
        WHERE id = $1
        RETURNING *
    """
    
    params = [item_id] + list(update_data.values()) + [datetime.utcnow()]
    
    try:
        row = await database_pool.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        return ItemResponse(**dict(row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int):
    query = "DELETE FROM items WHERE id = $1 RETURNING id"
    
    try:
        result = await database_pool.fetchval(query, item_id)
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))