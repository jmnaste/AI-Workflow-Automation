"""
Auth Service Client
Handles OAuth token vending requests to Auth service for service-to-service authentication.
"""
import os
import httpx
from typing import Optional
from datetime import datetime


# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
SERVICE_SECRET = os.getenv("SERVICE_SECRET")

# Token cache (simple in-memory cache per credential_id)
# Format: {credential_id: {"access_token": str, "expires_at": int}}
_token_cache: dict[str, dict] = {}


class AuthClientError(Exception):
    """Raised when Auth service token vending fails"""
    pass


async def get_credential_token(credential_id: str, force_refresh: bool = False) -> dict:
    """
    Request OAuth token for a credential from Auth service.
    
    Implements simple caching to avoid requesting tokens on every API call.
    Tokens are cached until 5 minutes before expiration.
    
    Args:
        credential_id: UUID of the credential
        force_refresh: If True, bypass cache and request new token
        
    Returns:
        dict with:
            - access_token: str - The OAuth access token
            - expires_at: int - Unix timestamp when token expires
            - token_type: str - Token type (usually "Bearer")
            
    Raises:
        AuthClientError: If token request fails
    """
    if not SERVICE_SECRET:
        raise AuthClientError("SERVICE_SECRET not configured")
    
    # Check cache if not forcing refresh
    if not force_refresh and credential_id in _token_cache:
        cached = _token_cache[credential_id]
        expires_at = cached.get("expires_at", 0)
        now = datetime.now().timestamp()
        
        # Return cached token if still valid (with 5 min buffer)
        if expires_at > now + 300:
            return cached
    
    # Request token from Auth service
    url = f"{AUTH_SERVICE_URL}/auth/oauth/internal/credential-token"
    headers = {
        "X-Service-Token": SERVICE_SECRET,
        "Content-Type": "application/json"
    }
    data = {"credential_id": credential_id}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Cache the token
            _token_cache[credential_id] = token_data
            
            return token_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise AuthClientError(
                    f"Credential {credential_id} not found or not connected"
                )
            elif e.response.status_code == 401:
                raise AuthClientError("Invalid SERVICE_SECRET")
            elif e.response.status_code == 400:
                error_detail = e.response.json().get("detail", "Unknown error")
                raise AuthClientError(f"Bad request: {error_detail}")
            else:
                raise AuthClientError(
                    f"Auth service error: {e.response.status_code} - {e.response.text}"
                )
        except httpx.RequestError as e:
            raise AuthClientError(f"Failed to reach Auth service: {str(e)}")


async def validate_credential_connected(credential_id: str) -> bool:
    """
    Check if a credential is connected and has valid tokens.
    
    Args:
        credential_id: UUID of the credential
        
    Returns:
        bool: True if connected and tokens available, False otherwise
    """
    try:
        token_data = await get_credential_token(credential_id)
        return bool(token_data.get("access_token"))
    except AuthClientError:
        return False


def clear_token_cache(credential_id: Optional[str] = None):
    """
    Clear token cache for a specific credential or all credentials.
    
    Useful when you know a token has been revoked or credential disconnected.
    
    Args:
        credential_id: If provided, clear only this credential's cache.
                      If None, clear entire cache.
    """
    global _token_cache
    
    if credential_id:
        _token_cache.pop(credential_id, None)
    else:
        _token_cache.clear()


def get_cache_stats() -> dict:
    """
    Get token cache statistics for monitoring.
    
    Returns:
        dict with cache size and credential IDs
    """
    return {
        "cached_credentials": len(_token_cache),
        "credential_ids": list(_token_cache.keys())
    }
