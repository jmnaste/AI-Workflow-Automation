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
