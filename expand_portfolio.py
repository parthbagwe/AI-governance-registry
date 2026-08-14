"""Add the extended sample portfolio without deleting existing registry data."""

from app.database import Base, SessionLocal, engine
from app.models.registry import MLModel
from app.sample_portfolio import expand_sample_portfolio

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    added = expand_sample_portfolio(db)
    total = db.query(MLModel).count()
finally:
    db.close()

print(f"Portfolio expanded: {added} new model(s), {total} total.")
print("   Forecastable demo_governance_health history is available on every model.")
