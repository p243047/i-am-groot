"""
FastAPI application factory.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db, close_db
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        description="Self-hosted AI Lead Generation Platform for business data enrichment",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    from app.api import auth, batches, leads, users, files, health
    
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(batches.router, prefix="/api/v1/batches", tags=["Batches"])
    app.include_router(leads.router, prefix="/api/v1/leads", tags=["Leads"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
    app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
    
    return app


# Create app instance
app = create_app()
