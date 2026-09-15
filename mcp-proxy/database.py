"""Database connection pool management."""
import asyncpg
import logging
from typing import Any, Optional, List
from contextlib import asynccontextmanager

from config import config

logger = logging.getLogger(__name__)

class DatabasePool:
    """Async PostgreSQL connection pool."""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool."""
        logger.info(f"Connecting to database: {config.DATABASE_URL.split('@')[1]}")
        
        self._pool = await asyncpg.create_pool(
            config.DATABASE_URL,
            min_size=config.DATABASE_POOL_MIN,
            max_size=config.DATABASE_POOL_MAX,
            command_timeout=60
        )
        
        logger.info("Database pool created successfully")
    
    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results."""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all rows."""
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch single row."""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args, column: int = 0) -> Any:
        """Fetch single value."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn

# Global database instance
db = DatabasePool()
