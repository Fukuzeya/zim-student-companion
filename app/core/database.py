# ============================================================================
# Database Connection
# ============================================================================
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import get_settings
import json

settings = get_settings()

# Define Base FIRST (very important)
class Base(DeclarativeBase):
    pass

# Convert postgresql:// to postgresql+asyncpg://
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Log connection info (hide password)
db_host = database_url.split('@')[1] if '@' in database_url else database_url
print(f"[DB] Connecting to database: {db_host}")

# Use NullPool in production to avoid connection pooling issues with asyncpg
# The asyncpg JSON codec setup can fail with pooled connections
if settings.DEBUG:
    # Development: use connection pooling
    engine = create_async_engine(
        database_url,
        echo=True,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
else:
    # Production: use NullPool to avoid asyncpg codec issues
    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
    )

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()