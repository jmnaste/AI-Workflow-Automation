import os
from fastapi import FastAPI, HTTPException

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # Optional import; endpoint will report if missing

app = FastAPI(title="AI Workflow API", version="0.1.0")


@app.get("/api/health")
def health():
    """Minimal liveness endpoint for UI and n8n checks."""
    return {"status": "ok"}


@app.get("/api/db/health")
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
        # Short connect timeout; simple round-trip
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version(), current_database(), current_user")
                version, dbname, user = cur.fetchone()
        return {"status": "ok", "database": dbname, "user": user, "version": str(version)}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"DB check failed: {e}")
