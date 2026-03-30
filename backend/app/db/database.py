"""
Database connection management for MATPOWER Web Backend.
Uses SQLAlchemy with aiosqlite for async SQLite operations.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path
from typing import AsyncGenerator
import os

# Database file path
DB_DIR = Path("E:/matpower-web/backend/data")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "matpower.db"

# SQLite connection string for aiosqlite
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database sessions.
    Yields an async session and ensures cleanup after use.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_engine():
    """Get the database engine."""
    return engine


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Call this on application startup.
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        from .models import (
            SimulationRecord,
            DisturbanceEvent,
            TimeSeriesData,
            ScenarioLabel,
            ExportTask,
        )

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close the database engine. Call on application shutdown."""
    await engine.dispose()
