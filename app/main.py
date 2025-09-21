from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from temporalio.client import Client

from .settings import get_settings, Settings
from .middleware import SecurityHeadersMiddleware
from .routers import health, uploads, jobs

settings: Settings = get_settings()

app: FastAPI = FastAPI(title="photo-api", version=settings.api_version)

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

temporal_client: Optional[Client] = None

@app.on_event("startup")
async def on_startup() -> None:
    """Initialize connections on app startup."""
    global temporal_client
    s: Settings = get_settings()
    temporal_client = await Client.connect(
        target_host=s.temporal_target, namespace=s.temporal_namespace
    )
    # Pass the temporal client to the jobs router
    jobs.set_temporal_client(temporal_client)

@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Clean up connections on app shutdown."""
    global temporal_client
    if temporal_client:
        await temporal_client.close()