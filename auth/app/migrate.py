import os
import sys
import logging

from alembic import command
from alembic.config import Config

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None


log = logging.getLogger("auth.migrate")


def _truthy(val: str | None) -> bool:
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def migrate_if_enabled() -> None:
    """Run Alembic migrations to head if MIGRATE_AT_START is enabled.

    Environment variables:
        - MIGRATE_AT_START: truthy to enable (default false)
        - MIGRATIONS_DATABASE_URL: optional override for DB (falls back to DATABASE_URL)
        - DATABASE_URL: default DB URL
    """
    if not _truthy(os.environ.get("MIGRATE_AT_START")):
        log.info("Migrations skipped: MIGRATE_AT_START is not enabled")
        return

    if psycopg is None:
        print("Fatal: psycopg not installed; cannot run migrations", file=sys.stderr)
        raise SystemExit(1)

    db_url = os.environ.get("MIGRATIONS_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("Fatal: DATABASE_URL or MIGRATIONS_DATABASE_URL must be set", file=sys.stderr)
        raise SystemExit(1)

    # Ensure Alembic sees the URL (env.py also reads from env)
    os.environ.setdefault("DATABASE_URL", db_url)

    # Advisory lock key for auth migrations (arbitrary stable bigint)
    lock_key = 5314019919001234567

    # Acquire advisory lock to serialize concurrent starts
    import time

    attempts = int(os.environ.get("MIGRATIONS_CONNECT_ATTEMPTS", "12"))
    delay_seconds = int(os.environ.get("MIGRATIONS_CONNECT_DELAY", "5"))

    for attempt in range(1, attempts + 1):
        try:
            with psycopg.connect(db_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
                    locked = cur.fetchone()[0]
                    if not locked:
                        print("Another auth migration is in progress; waiting for lock...", file=sys.stderr)
                        # Block until available
                        cur.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
            break
        except Exception as e:
            if attempt == attempts:
                print(f"Failed to connect to DB for migrations after {attempts} attempts: {e}", file=sys.stderr)
                raise
            time.sleep(delay_seconds)

    # Run Alembic upgrade to head
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    # Normalize path
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    # Let env.py read from env; also set here for good measure
    cfg.set_main_option("sqlalchemy.url", db_url)

    print("Running auth DB migrations to head...", file=sys.stderr)
    command.upgrade(cfg, "head")
    print("Auth DB migrations complete", file=sys.stderr)
    finally:
        # Always release lock if we acquired it
        try:
            with psycopg.connect(db_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        except Exception:
            # Best-effort unlock; log and proceed
            pass


if __name__ == "__main__":
    migrate_if_enabled()
