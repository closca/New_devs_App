import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import logging
from ..config import settings

logger = logging.getLogger(__name__)


def _async_database_url(url: str) -> str:
    """Rewrite a plain postgresql:// URL to use the asyncpg driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    return url


class DatabasePool:
    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection pool"""
        if self.session_factory is not None:
            return
        try:
            # Create async engine with connection pooling.
            # DATABASE_URL is the single source of truth (see docker-compose.yml / config.py).
            database_url = _async_database_url(settings.database_url)

            # Note: the async engine picks AsyncAdaptedQueuePool by default;
            # passing sqlalchemy.pool.QueuePool here raises ArgumentError.
            self.engine = create_async_engine(
                database_url,
                pool_size=20,  # Number of connections to maintain
                max_overflow=30,  # Additional connections when needed
                pool_pre_ping=True,  # Validate connections
                pool_recycle=3600,  # Recycle connections every hour
                echo=False  # Set to True for SQL debugging
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("✅ Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"❌ Database pool initialization failed: {e}")
            self.engine = None
            self.session_factory = None
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
    
    def get_session(self) -> AsyncSession:
        """Get database session from pool.

        Intentionally synchronous: callers use `async with db_pool.get_session() as session:`,
        which requires the AsyncSession itself, not a coroutine wrapping it.
        """
        if not self.session_factory:
            raise Exception("Database pool not initialized")
        return self.session_factory()

# Global database pool instance
db_pool = DatabasePool()

async def get_db_session() -> AsyncSession:
    """Dependency to get database session"""
    async with db_pool.get_session() as session:
        yield session
