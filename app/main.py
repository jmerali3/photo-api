from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from temporalio.client import Client

from app.settings import get_settings, Settings
from app.middleware import SecurityHeadersMiddleware
from app.routers import health, uploads, jobs, admin
from app.database import init_database, create_tables, close_db

settings: Settings = get_settings()

# Global variable for temporal client
temporal_client: Optional[Client] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown logic.
    """
    global temporal_client
    s: Settings = get_settings()

    # Startup
    print("Starting up photo-api...")

    # Initialize database connection
    init_database()

    # Create database tables
    await create_tables()

    # Initialize Temporal client
    try:
        temporal_client = await Client.connect(
            target_host=s.temporal_target, namespace=s.temporal_namespace
        )
        # Pass the temporal client to the jobs router
        jobs.set_temporal_client(temporal_client)
        print("✅ Temporal client connected")
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to Temporal: {e}")
        print("API will run without Temporal workflows")

    print("✅ Photo-api startup complete")

    yield

    # Shutdown
    print("Shutting down photo-api...")

    # Close Temporal client
    if temporal_client:
        try:
            await temporal_client.close()
            print("✅ Temporal client closed")
        except Exception as e:
            print(f"Error closing Temporal client: {e}")

    # Close database connections
    await close_db()
    print("✅ Photo-api shutdown complete")

app: FastAPI = FastAPI(
    title="photo-api",
    version=settings.api_version,
    lifespan=lifespan
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS for local client to hosted backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(uploads.router)
app.include_router(jobs.router)
app.include_router(admin.router)