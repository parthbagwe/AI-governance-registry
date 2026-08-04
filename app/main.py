from fastapi import FastAPI

from app.database import Base, engine
from app.api.routes import router
from fastapi.middleware.cors import CORSMiddleware
# Ensure tables exist (idempotent — won't touch existing data)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Model Governance Registry",
    description=(
        "Tracks ML/LLM/SLM models through a pilot -> review -> production -> "
        "deprecated lifecycle, with a five-dimension governance scorecard, "
        "audit trail, and data lineage tracking."
    ),
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your actual Vercel URL once you have it
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1", tags=["registry"])


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}