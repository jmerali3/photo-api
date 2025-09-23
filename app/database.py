from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Integer
from datetime import datetime
import uuid
import logging

from .settings import get_settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class JobLog(Base):
    """
    Log table for tracking jobs sent to Temporal.
    Records metadata about what files/URLs were processed.
    """
    __tablename__ = "job_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False, unique=True, index=True)
    job_type = Column(String, nullable=False)  # "upload" or "url"

    # File information
    filename = Column(String, nullable=True)  # Original filename for uploads
    s3_key = Column(String, nullable=True)    # S3 key for uploads
    source_url = Column(String, nullable=True)  # Source URL for url jobs
    content_type = Column(String, nullable=True)

    # Metadata
    job_metadata = Column(Text, nullable=True)  # JSON string of additional metadata

    # Temporal info
    temporal_workflow_id = Column(String, nullable=False)
    temporal_task_queue = Column(String, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Status tracking
    status = Column(String, default="submitted", nullable=False)
    error_message = Column(Text, nullable=True)

# Database connection
settings = get_settings()

# Global variables that will be set during app startup
engine: Optional[object] = None
AsyncSessionLocal: Optional[object] = None
database_enabled = False

def init_database():
    """Initialize database connection. Call this during app startup."""
    global engine, AsyncSessionLocal, database_enabled

    try:
        # Create async engine
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # Log SQL queries in debug mode
            pool_size=5,
            max_overflow=10,
        )

        # Create session factory
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        database_enabled = True
        logger.info("Database connection initialized successfully")

    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.warning("Running without database logging")
        database_enabled = False

async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Dependency to get database session.
    Use this in FastAPI route dependencies.
    Returns None if database is not available.
    """
    if not database_enabled or not AsyncSessionLocal:
        yield None
        return

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Create all database tables."""
    if not database_enabled or not engine:
        logger.warning("Skipping table creation - database not available")
        return

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

async def close_db():
    """Close database connections."""
    if engine:
        try:
            await engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")