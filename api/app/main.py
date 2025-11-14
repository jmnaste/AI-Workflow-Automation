import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # Optional import; endpoint will report if missing

from .services.migrations import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database migrations and check auth version on startup."""
    try:
        run_migrations()
        print("Database migrations completed successfully")
        
        # Check auth schema version if required
        check_auth_schema_version()
        
    except Exception as e:
        print(f"Startup failed: {e}")
        raise
    yield


app = FastAPI(title="AI Workflow API", version="0.1.0", lifespan=lifespan)


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
                current = row['semver'] if row else None
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
                cur.execute("SELECT version() as version, current_database() as dbname, current_user as user")
                row = cur.fetchone()
                version, dbname, user = row['version'], row['dbname'], row['user']
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


# ============================================================================
# Test Endpoints (for development/debugging)
# ============================================================================

@app.get("/api/test/auth-token/{credential_id}")
async def test_auth_token(credential_id: str):
    """
    Test endpoint for Auth service token vending.
    
    Tests the auth_client service by requesting a token for the given credential.
    Returns token metadata (not the actual token for security).
    """
    from .services.auth_client import get_credential_token, AuthClientError
    
    try:
        token_data = await get_credential_token(credential_id)
        
        # Return metadata only (not actual token)
        return {
            "status": "success",
            "credential_id": credential_id,
            "has_token": bool(token_data.get("access_token")),
            "token_length": len(token_data.get("access_token", "")),
            "expires_at": token_data.get("expires_at"),
            "token_type": token_data.get("token_type")
        }
    except AuthClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/api/test/auth-validate/{credential_id}")
async def test_auth_validate(credential_id: str):
    """
    Test endpoint to validate if a credential is connected.
    
    Returns boolean indicating if credential has valid tokens.
    """
    from .services.auth_client import validate_credential_connected
    
    is_connected = await validate_credential_connected(credential_id)
    
    return {
        "status": "success",
        "credential_id": credential_id,
        "is_connected": is_connected
    }


@app.get("/api/test/auth-cache")
def test_auth_cache():
    """
    Get token cache statistics for monitoring.
    """
    from .services.auth_client import get_cache_stats
    
    return get_cache_stats()
