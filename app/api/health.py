from fastapi import APIRouter, HTTPException
from app.database.connection import database_pool
from datetime import datetime

router = APIRouter()


@router.get("/")
async def health_check():
    try:
        await database_pool.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status
    }


@router.get("/ready")
async def readiness_check():
    try:
        await database_pool.fetchval("SELECT 1")
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service not ready")