import asyncpg
from typing import Optional
from app.core.config import settings


class DatabasePool:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Connect to PostgreSQL via Cloud SQL Proxy or Unix socket"""
        # Check if running on Cloud Run with Unix socket
        if settings.CLOUD_SQL_CONNECTION_NAME:
            # Cloud Run uses Unix sockets
            host = f"/cloudsql/{settings.CLOUD_SQL_CONNECTION_NAME}"
            port = None
            self.pool = await asyncpg.create_pool(
                host=host,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=10,
                max_size=20,
                command_timeout=60
            )
        else:
            # Local development with Cloud SQL Proxy
            self.pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=10,
                max_size=20,
                command_timeout=60
            )
        print(f"Connected to NWSL database: {settings.DB_NAME}")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            print("Database connection closed")

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)


database_pool = DatabasePool()