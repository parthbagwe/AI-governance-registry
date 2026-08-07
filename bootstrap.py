"""
First-run setup for a deployed instance.

A hosted Postgres starts empty, and free hosting tiers generally don't give
you a shell to run `seed.py` in. So this runs as part of the start command:
it creates the tables, and if — and only if — the registry has no models at
all, it loads the sample portfolio so the deployment isn't a blank page.

The emptiness check is the entire safety mechanism. `seed.py` drops every
table before rebuilding, which is exactly right on a laptop and catastrophic
against a registry someone has been using. So it is only ever invoked when
there is demonstrably nothing to lose, and even that can be turned off with
SKIP_BOOTSTRAP_SEED=1.

Run directly if you want: `python bootstrap.py`
"""

import os
import runpy
import sys

from app.database import Base, engine
from app.models.registry import MLModel  # noqa: F401 — registers the table
from app.database import SessionLocal


def main() -> int:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables ready.")

    if os.getenv("SKIP_BOOTSTRAP_SEED", "").strip() in ("1", "true", "True"):
        print("↩️  SKIP_BOOTSTRAP_SEED is set — leaving the registry as it is.")
        return 0

    db = SessionLocal()
    try:
        count = db.query(MLModel).count()
    finally:
        db.close()

    if count > 0:
        print(f"↩️  Registry already holds {count} model(s) — not seeding.")
        print("   Seeding would drop them. Nothing to do.")
        return 0

    print("🌱 Registry is empty — loading the sample portfolio…")
    # Executed as a script rather than imported, because seed.py does its work
    # at module level. Safe here precisely because we just proved the registry
    # is empty.
    runpy.run_path("seed.py", run_name="__main__")
    print("✅ Bootstrap complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
