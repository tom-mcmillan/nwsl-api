import secrets
import string
from datetime import datetime
from typing import Optional
from app.database.connection import database_pool


def generate_api_key() -> str:
    """Generate a secure API key in OpenAI style format."""
    # Format: nwsl_live_[48 random characters]
    # Similar to OpenAI's sk-proj-[random] format
    random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
    return f"nwsl_live_{random_part}"


async def create_api_key(name: str, email: str) -> dict:
    """Create a new API key for a developer."""
    api_key = generate_api_key()
    
    query = """
        INSERT INTO api_keys (key, name, email, created_at, is_active)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, key, name, email, created_at
    """
    
    result = await database_pool.fetchrow(
        query,
        api_key,
        name,
        email,
        datetime.utcnow(),
        True
    )
    
    return dict(result)


async def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate an API key and return user info if valid."""
    if not api_key:
        return None
    
    # Update last_used and usage_count
    query = """
        UPDATE api_keys 
        SET last_used = $2, usage_count = usage_count + 1
        WHERE key = $1 AND is_active = TRUE
        RETURNING id, name, email, rate_limit, usage_count
    """
    
    result = await database_pool.fetchrow(
        query,
        api_key,
        datetime.utcnow()
    )
    
    return dict(result) if result else None


async def get_user_keys(email: str) -> list:
    """Get all API keys for a user."""
    query = """
        SELECT id, key, name, created_at, last_used, usage_count, is_active
        FROM api_keys
        WHERE email = $1
        ORDER BY created_at DESC
    """
    
    results = await database_pool.fetch(query, email)
    return results


async def revoke_api_key(key_id: str, email: str) -> bool:
    """Revoke an API key (soft delete)."""
    query = """
        UPDATE api_keys
        SET is_active = FALSE
        WHERE id = $1 AND email = $2
        RETURNING id
    """
    
    result = await database_pool.fetchrow(query, key_id, email)
    return result is not None


async def check_rate_limit(api_key: str) -> tuple[bool, dict]:
    """Check if API key has exceeded rate limit."""
    # For now, just return True (no rate limiting)
    # In production, you'd check against Redis or similar
    return True, {"limit": 1000, "remaining": 999}