"""
Database connection and session management.
Supports both PostgreSQL and SQLite.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings
import os

settings = get_settings()

# Auto-detect database type if DATABASE_URL is empty or use provided URL
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    # Use SQLite as fallback for systems without PostgreSQL
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATA_DIR, 'leadgen.db')}"
    print(f"[INFO] Using SQLite database at {DATABASE_URL}")
elif DATABASE_URL.startswith("postgresql"):
    print(f"[INFO] Using PostgreSQL database")

# Create async engine with SQLite-compatible settings for small deployments
if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=40,
    )

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection."""
    await engine.dispose()
