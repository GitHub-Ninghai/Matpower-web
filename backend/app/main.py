"""
FastAPI Main Application
MATPOWER Web Visualization Platform Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.engine import get_engine, cleanup_engine
from app.api.routes import cases, simulation, disturbance, data
from app.api import ws
from app.db.database import init_db as init_database, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting MATPOWER Web Backend...")
    logger.info(f"MATPOWER path: {settings.MATPOWER_PATH}")

    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")

        # Initialize Octave engine
        engine = get_engine()
        if engine.is_initialized:
            logger.info("Octave/MATPOWER engine initialized successfully")

            # List available cases
            available_cases = engine.list_cases()
            logger.info(f"Found {len(available_cases)} test cases")
            for case in available_cases[:5]:  # Log first 5
                logger.info(f"  - {case['name']}: {case['buses']} buses")

        else:
            logger.warning("Octave engine not initialized")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

    yield

    # Shutdown
    logger.info("Shutting down MATPOWER Web Backend...")
    cleanup_engine()
    await close_db()
    logger.info("Database closed")


# Create FastAPI application
app = FastAPI(
    title="MATPOWER Web API",
    description="REST API for MATPOWER power system simulation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cases.router)
app.include_router(simulation.router)
app.include_router(disturbance.router)
app.include_router(data.router)
app.include_router(ws.router)


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "MATPOWER Web API",
        "version": "1.0.0",
        "description": "REST API for MATPOWER power system simulation",
        "endpoints": {
            "cases": "/api/cases",
            "simulation": "/api/simulation",
            "disturbance": "/api/disturbance",
            "data": "/api/data",
            "websocket": "/ws/simulation/{client_id}",
            "monitor": "/ws/monitor/{client_id}"
        },
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    engine = get_engine()
    return {
        "status": "healthy",
        "octave_initialized": engine.is_initialized if engine else False,
        "matpower_path": settings.MATPOWER_PATH
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
