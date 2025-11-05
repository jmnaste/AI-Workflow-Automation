import os
from fastapi import FastAPI, HTTPException

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # Optional import; endpoint will report if missing

app = FastAPI(title="Auth Service", version="0.1.0")


@app.get("/auth/health")
def health():
    """Minimal liveness endpoint for internal checks."""
    return {"status": "ok"}


@app.get("/auth/db/health")
def db_health():
    """Lightweight DB connectivity check using DATABASE_URL.

    Returns:
        { status: "ok" | "skipped" | "error", details?: str }
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return {"status": "skipped", "details": "DATABASE_URL not set"}
    if psycopg is None:
        raise HTTPException(status_code=500, detail="psycopg not installed in image")
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version(), current_database(), current_user")
                version, dbname, user = cur.fetchone()
        return {"status": "ok", "database": dbname, "user": user, "version": str(version)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"DB check failed: {e}")


@app.get("/auth/egress/health")
def egress_health(url: str | None = None):
    """Simple outbound HTTP check.

    Args:
        url: Optional override of the target URL. If not provided, uses
             EXTERNAL_PING_URL env var or defaults to https://example.com.

    Returns:
        JSON with status ok and the HTTP status code from the target on success.
    """
    target = url or os.environ.get("EXTERNAL_PING_URL", "https://example.com")
    try:
        import urllib.request

        with urllib.request.urlopen(target, timeout=3) as resp:  # nosec B310
            code = resp.getcode()
            return {"status": "ok", "url": target, "code": int(code)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Egress failed: {e}")


@app.get("/auth/versions")
def versions(n: int = 5):
    """Return the last n applied schema versions for the auth service (newest first).

    If the history table is not present yet, falls back to the single current entry
    from auth.schema_registry (if available).
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return []
    if psycopg is None:
        raise HTTPException(status_code=500, detail="psycopg not installed in image")

    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                # Try history first
                try:
                    cur.execute(
                        (
                            "SELECT service, semver, ts_key, alembic_rev, applied_at "
                            "FROM auth.schema_registry_history WHERE service='auth' "
                            "ORDER BY applied_at DESC LIMIT %s"
                        ),
                        (max(1, min(n, 100)),),
                    )
                    rows = cur.fetchall()
                except Exception:
                    rows = []

                if not rows:
                    # Fallback to single pointer row
                    cur.execute(
                        "SELECT service, semver, ts_key, alembic_rev, applied_at FROM auth.schema_registry WHERE service='auth'"
                    )
                    one = cur.fetchone()
                    if one:
                        rows = [one]
        return [
            {
                "service": r[0],
                "semver": r[1],
                "ts_key": int(r[2]) if r[2] is not None else None,
                "alembic_rev": r[3],
                "applied_at": r[4].isoformat() if r[4] is not None else None,
            }
            for r in rows
        ]
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Version lookup failed: {e}")
