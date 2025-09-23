from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Integer
from datetime import datetime
import uuid

from .settings import get_settings

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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    Use this in FastAPI route dependencies.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close database connections."""
    await engine.dispose()