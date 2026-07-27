"""
Database configuration.

In this prototype we use SQLite (file-based, zero-setup) so the project runs
anywhere without a Postgres server. In production this would just be:

    DATABASE_URL = "postgresql://user:pass@host:5432/ai_governance"

...and you'd swap JSON columns for JSONB, and Integer PKs for BIGSERIAL.
Everything else in the schema is written to be portable between the two.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./governance.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed only for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()