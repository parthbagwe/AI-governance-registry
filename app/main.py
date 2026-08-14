import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, DATABASE_URL
from app.api.routes import router
from app.auth import require_actor

# Ensure tables exist (idempotent — won't touch existing data).
# Note: this creates tables that are missing; it does not alter existing ones.
# Adding a constraint to a table that already exists needs a fresh database
# (locally, `python seed.py`) or a real migration tool.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Model Governance Registry",
    description=(
        "Tracks ML/LLM/SLM models through a pilot -> review -> production -> "
        "deprecated lifecycle, with risk-tiered promotion gates, a five-dimension "
        "governance scorecard, an emergency kill switch, an append-only audit "
        "trail, and data lineage tracking."
    ),
    version="1.0.0",
)

# Which browsers may call this API.
#
# Defaults to "*" so a fresh clone works with no configuration. In a real
# deployment set ALLOWED_ORIGINS to the actual frontend URL — a governance
# tool that any page on the internet can POST approvals to is not one.
# Comma-separated, e.g.:
#   ALLOWED_ORIGINS=https://my-app.vercel.app,http://localhost:3000
_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Authentication uses an Authorization header rather than cross-origin
    # cookies, so credentialed CORS requests are not required.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    router,
    prefix="/api/v1",
    tags=["registry"],
    dependencies=[Depends(require_actor)],
)


@app.get("/")
def root():
    return {
        "service": "AI Model Governance Registry",
        "status": "ok",
        "docs": "/docs",
        "api": "/api/v1/models",
    }


@app.get("/health")
def health():
    """
    Liveness probe for the hosting platform.

    Reports which database backend is in use — without the credentials — so a
    misconfigured deployment silently falling back to ephemeral SQLite is
    visible rather than something you discover when the data vanishes after a
    redeploy.
    """
    backend = DATABASE_URL.split("://", 1)[0] if "://" in DATABASE_URL else "unknown"
    return {
        "status": "ok",
        "database": backend,
        "persistent": backend.startswith("postgres"),
    }
