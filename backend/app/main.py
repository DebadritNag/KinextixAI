"""
Kinetix AI - Intelligent Supply Chain Optimization System

FastAPI backend providing data ingestion, ML inference, and optimization
services. All data is held in-memory with no external database required.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("kinetix")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle.

    Startup: Initialize in-memory data store, load ML models, and start
    the simulation loop.
    Shutdown: Gracefully stop the simulation loop and release resources.
    """
    from app.services.simulation import SimulationManager

    logger.info("Kinetix AI backend starting up...")

    simulation = SimulationManager()
    await simulation.start()
    logger.info("Startup complete. Ready to serve requests.")

    yield

    await simulation.stop()
    logger.info("Kinetix AI backend shutting down...")


app = FastAPI(
    title="Kinetix AI",
    description=(
        "Intelligent Supply Chain Optimization System — "
        "predicts disruptions, optimizes routing, and explains decisions."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware: allow the Flutter frontend to connect from any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return structured error responses for unhandled exceptions (Req 15.4)."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ── Register API routers ──────────────────────────────────────────────
from app.api.shipments import router as shipments_router
from app.api.alerts import router as alerts_router
from app.api.optimize import router as optimize_router
from app.api.explain import router as explain_router
from app.api.analytics import router as analytics_router
from app.api.settings import router as settings_router
from app.api.auth import router as auth_router
from app.api.demo import router as demo_router

app.include_router(shipments_router)
app.include_router(alerts_router)
app.include_router(optimize_router)
app.include_router(explain_router)
app.include_router(analytics_router)
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(demo_router)


@app.get("/api/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "success",
        "data": {"service": "kinetix-ai", "version": "0.1.0"},
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
