from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.core.api_keys import validate_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key against database."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key required. Get one at /register"
        )
    
    # Check if it's the demo key (backwards compatibility)
    if api_key == settings.DEMO_API_KEY:
        return {"name": "Demo User", "email": "demo@nwsl-api.com"}
    
    # Validate against database
    key_info = await validate_api_key(api_key)
    
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return key_info