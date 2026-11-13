"""
=========================================================================================
main.py — Privacy Gateway AI Application Factory & Lifespan Controller
=========================================================================================

Tech Stack:
 - FastAPI / Starlette (High-performance async ASGI web framework)
 - Python 3.11+ / Uvicorn (Production ASGI application server)
 - SQLAlchemy (ORM for relational database persistence)
 - Pydantic (Type validation and environment settings management)

Key Architectural Responsibilities:
 1. Application Lifespan & Initialization:
    - Runs automatic relational schema synchronization (`Base.metadata.create_all`).
    - Seeds default enterprise demo roles, users, and baseline governance policies.
    - Pre-warms the Indic NER and regex-based PII detection engine to eliminate cold starts.
 
 2. CORS & Middleware:
    - Configures enterprise Cross-Origin Resource Sharing (CORS) rules to secure
      API interactions with the React frontend dashboard.

 3. Modular Router Dispatch:
    - Mounts v1 API routers:
      * `/api/v1/auth`: JWT authentication, RBAC profile management.
      * `/api/v1/gateway`: Ingestion, masking, outbound security gate, LLM dispatch, restoration.
      * `/api/v1/governance`: Purpose-bound policy administration and audit query engine.

 4. System Health & Readiness:
    - Exposes `/health` endpoint providing live status of database, privacy vault,
      and PII detection subsystems for Kubernetes / Docker container health checks.
=========================================================================================
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

_VENDOR_DIR = Path(__file__).resolve().parents[1] / ".vendor"
if _VENDOR_DIR.is_dir() and str(_VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(_VENDOR_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.auth import router as auth_router
from app.api.v1.gateway import router as gateway_router
from app.api.v1.governance import router as governance_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.session import Base, SessionLocal, engine
from app.services.auth_service import ensure_seed_data
from app.services.detection.engine import DetectionEngineError, get_detection_engine
from app.services.privacy_vault.vault import get_privacy_vault

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_seed_data(db)

    try:
        get_detection_engine().initialize()
    except DetectionEngineError as exc:
        logger.error("startup_detector_warmup_failed", error=str(exc))

    logger.info("privacy_gateway_started", environment=settings.ENVIRONMENT)
    yield


app = FastAPI(
    title="Privacy Gateway AI",
    description="DPDP-Ready Enterprise AI Privacy & Governance Control Plane (MINEARENA 1.0 PS-02)",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(gateway_router)
app.include_router(governance_router)


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check() -> dict:
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    redis_ok = get_privacy_vault().health_check()

    detector_ok = False
    try:
        get_detection_engine().initialize()
        detector_ok = True
    except Exception:
        detector_ok = False

    overall = "healthy" if (db_ok and redis_ok and detector_ok) else "degraded"
    return {
        "status": overall,
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": "up" if db_ok else "down",
            "redis_vault": "up" if redis_ok else "down",
            "local_pii_detector": "up" if detector_ok else "down",
        },
    }
