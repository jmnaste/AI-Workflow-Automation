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
    mig_flag = os.environ.get("MIGRATE_AT_START")
    print(f"=== AUTH MIGRATION ENTER === MIGRATE_AT_START={mig_flag}", file=sys.stderr)
    if not _truthy(mig_flag):
        log.info("Migrations skipped: MIGRATE_AT_START is not enabled")
        print("=== AUTH MIGRATION SKIP (disabled) ===", file=sys.stderr)
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

    # Track summary for logging
    head_summary = None
    current_rev_summary = None
    service_semver_summary = None

    # Run Alembic upgrade to head and record pointer/history
    try:
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        # Normalize path
        cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
        # Let env.py read from env; also set here for good measure
        cfg.set_main_option("sqlalchemy.url", db_url)
    # Read configured version table fully-qualified target
    vtable = cfg.get_main_option("version_table") or "alembic_version_auth"
    vschema = cfg.get_main_option("version_table_schema") or "auth"

        print("Running auth DB migrations to head...", file=sys.stderr)
        command.upgrade(cfg, "head")
        print("Auth DB migrations complete", file=sys.stderr)

        # After successful upgrade, record current revision in registry and append to history if changed
        try:
            from app.main import app as fastapi_app  # to read service version
            service_semver = getattr(fastapi_app, "version", None) or os.environ.get("SERVICE_SEMVER") or "0.0.0"
        except Exception:
            service_semver = os.environ.get("SERVICE_SEMVER") or "0.0.0"

        import datetime as _dt
        ts_key = int(_dt.datetime.utcnow().strftime("%Y%m%d%H%M"))

        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Read current alembic head from the known/likely tables
                head = None
                for stmt in (
                    f"SELECT version_num FROM {vschema}.{vtable} LIMIT 1",
                    f"SELECT version_num FROM {vschema}.alembic_version LIMIT 1",
                    "SELECT version_num FROM public.alembic_version LIMIT 1",
                ):
                    try:
                        cur.execute(stmt)
                        head = (cur.fetchone() or [None])[0]
                        if head:
                            break
                    except Exception as e:
                        # Try next
                        print(
                            f"\n!!! AUTH MIGRATION ROLLBACK: head probe failed for stmt: {stmt}\n    error: {e}\n",
                            file=sys.stderr,
                        )
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                # If no head recorded (empty version table), stamp to head so future runs are consistent
                if not head:
                    try:
                        print("Alembic version table empty; stamping to head...", file=sys.stderr)
                        command.stamp(cfg, "head")
                        # Re-read after stamping
                        for stmt in (
                            f"SELECT version_num FROM {vschema}.{vtable} LIMIT 1",
                            f"SELECT version_num FROM {vschema}.alembic_version LIMIT 1",
                            "SELECT version_num FROM public.alembic_version LIMIT 1",
                        ):
                            try:
                                cur.execute(stmt)
                                head = (cur.fetchone() or [None])[0]
                                if head:
                                    break
                            except Exception as e:
                                print(
                                    f"\n!!! AUTH MIGRATION ROLLBACK: post-stamp head probe failed for stmt: {stmt}\n    error: {e}\n",
                                    file=sys.stderr,
                                )
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass
                        # Do not force-create the version table; rely on Alembic config to manage it
                    except Exception as e:
                        # Best effort; proceed to registry update even if stamping failed
                        print(f"Warning: failed to auto-stamp Alembic head: {e}", file=sys.stderr)
                # Ensure registry tables exist (belt-and-suspenders in case revisions differed)
                try:
                    cur.execute("CREATE SCHEMA IF NOT EXISTS auth")
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS auth.schema_registry (
                            service text PRIMARY KEY,
                            semver text NOT NULL,
                            ts_key bigint NOT NULL,
                            alembic_rev text NOT NULL,
                            applied_at timestamptz NOT NULL DEFAULT now()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS auth.schema_registry_history (
                            id bigserial PRIMARY KEY,
                            service text NOT NULL,
                            semver text NOT NULL,
                            ts_key bigint NOT NULL,
                            alembic_rev text NOT NULL,
                            applied_at timestamptz NOT NULL DEFAULT now()
                        )
                        """
                    )
                except Exception as e:
                    print(
                        f"\n!!! AUTH MIGRATION ROLLBACK: failed to ensure registry/history tables\n    error: {e}\n",
                        file=sys.stderr,
                    )
                    # If we can't create (e.g., perms), proceed without fataling
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                # Read pointer row
                try:
                    cur.execute("SELECT alembic_rev FROM auth.schema_registry WHERE service='auth'")
                    row = cur.fetchone()
                except Exception as e:
                    print(
                        f"\n!!! AUTH MIGRATION ROLLBACK: failed to read schema_registry pointer\n    error: {e}\n",
                        file=sys.stderr,
                    )
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    row = None
                current_rev = row[0] if row else None
                if head and head != current_rev:
                    # Upsert pointer
                    cur.execute(
                        (
                            "INSERT INTO auth.schema_registry(service, semver, ts_key, alembic_rev) "
                            "VALUES ('auth', %s, %s, %s) "
                            "ON CONFLICT (service) DO UPDATE SET semver=EXCLUDED.semver, ts_key=EXCLUDED.ts_key, alembic_rev=EXCLUDED.alembic_rev, applied_at=now()"
                        ),
                        (service_semver, ts_key, head),
                    )
                    # Append to history
                    cur.execute(
                        (
                            "INSERT INTO auth.schema_registry_history(service, semver, ts_key, alembic_rev) "
                            "VALUES ('auth', %s, %s, %s)"
                        ),
                        (service_semver, ts_key, head),
                    )
                # Capture summary for logs
                head_summary = head
                current_rev_summary = current_rev
                service_semver_summary = service_semver
                print(
                    f"=== AUTH MIGRATION DONE === head={head_summary} pointer={current_rev_summary} semver={service_semver_summary}",
                    file=sys.stderr,
                )
    finally:
        # Always release lock if we acquired it
        try:
            with psycopg.connect(db_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        except Exception:
            # Best-effort unlock; log and proceed
            pass
        print("=== AUTH MIGRATION EXIT ===", file=sys.stderr)


if __name__ == "__main__":
    migrate_if_enabled()
