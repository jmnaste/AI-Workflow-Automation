import os
from fastapi import FastAPI, HTTPException

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # Optional import; endpoint will report if missing

app = FastAPI(title="AI Workflow API", version="0.1.0")


def _parse_semver(s: str) -> tuple[int, int, int]:
    parts = (s or "0.0.0").split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except Exception:
        # Non-numeric fallback: treat as 0.0.0
        major, minor, patch = 0, 0, 0
    return major, minor, patch


@app.on_event("startup")
def check_auth_schema_version():
    """Optionally gate API startup on a minimum Auth schema version.

    Set API_MIN_AUTH_VERSION to a semver (e.g., 0.1.0). If set, we will query
    auth.schema_registry and ensure the 'auth' service semver >= required.
    If unmet, raise to fail startup so the orchestrator can restart after auth migrates.
    """
    required = os.environ.get("API_MIN_AUTH_VERSION")
    if not required:
        return
    dsn = os.environ.get("DATABASE_URL")
    if not dsn or psycopg is None:
        # If we can't check, proceed but warn via exception to surface misconfig
        raise RuntimeError("API_MIN_AUTH_VERSION set but DATABASE_URL/psycopg missing; cannot verify")
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT semver FROM auth.schema_registry WHERE service = 'auth'"
                )
                row = cur.fetchone()
                current = row[0] if row else None
    except Exception as e:
        raise RuntimeError(f"Failed to check auth schema_registry: {e}")

    if not current:
        raise RuntimeError("Auth schema_registry missing; Auth migrations likely not applied yet")

    if _parse_semver(current) < _parse_semver(required):
        raise RuntimeError(
            f"Auth schema too old: have {current}, require >= {required}. Wait for Auth to migrate."
        )


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


@app.get("/api/egress/health")
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
