"""OAuth routes for external provider authentication."""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from typing import Dict, Any
from uuid import UUID
from ..services import oauth
from ..services.jwt import verify_jwt


router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


@router.get("/ms365/authorize")
async def ms365_authorize(request: Request):
    """
    Initiate MS365 OAuth flow.
    
    Requires authenticated user (JWT in Authorization header or cookie).
    Generates OAuth state and redirects to Microsoft login.
    """
    # Extract user from JWT (from Authorization header or cookie)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = auth_header.replace("Bearer ", "")
    try:
        payload = verify_jwt(token)
        user_id = UUID(payload["userId"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    # Build authorization URL with state
    auth_url = oauth.build_ms365_authorize_url(user_id)
    
    return RedirectResponse(url=auth_url)


@router.get("/ms365/callback")
async def ms365_callback(code: str = None, state: str = None, error: str = None, error_description: str = None):
    """
    Handle MS365 OAuth callback.
    
    Receives authorization code, exchanges for tokens, stores encrypted tokens,
    and redirects to UI success page.
    """
    # Check for OAuth errors
    if error:
        error_msg = error_description or error
        # Redirect to UI with error
        return RedirectResponse(url=f"/admin/tenants?error={error_msg}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    # Validate state (CSRF protection)
    user_id = oauth.validate_oauth_state(state, "ms365")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    try:
        # Exchange code for tokens
        tokens = await oauth.exchange_code_for_tokens(code)
        
        # Get user info from Microsoft Graph
        user_info = await oauth.get_ms365_user_info(tokens["access_token"])
        
        external_account_id = user_info.get("userPrincipalName") or user_info.get("mail")
        display_name = user_info.get("displayName") or external_account_id
        
        # Create or update tenant
        tenant_id = oauth.create_or_update_tenant(
            provider="ms365",
            external_account_id=external_account_id,
            external_tenant_id=None,  # MS365 tenant ID is in user_info if needed
            display_name=display_name
        )
        
        # Store encrypted tokens
        oauth.store_tenant_tokens(tenant_id, tokens, token_type="delegated")
        
        # Redirect to UI success page
        return RedirectResponse(url="/admin/tenants?success=true")
        
    except Exception as e:
        # Redirect to UI with error
        return RedirectResponse(url=f"/admin/tenants?error={str(e)}")


# Internal endpoint for API service to request tokens
@router.post("/internal/tenant-token")
async def get_tenant_token_internal(request: Request) -> Dict[str, Any]:
    """
    Internal endpoint for API service to request tenant access token.
    
    Requires X-Service-Token header for authentication.
    Returns valid access token, refreshing if needed.
    """
    import os
    
    # Validate service token
    service_token = request.headers.get("X-Service-Token")
    expected_token = os.environ.get("SERVICE_SECRET")
    
    if not service_token or service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    
    # Get tenant_id from request body
    body = await request.json()
    tenant_id_str = body.get("tenant_id")
    
    if not tenant_id_str:
        raise HTTPException(status_code=400, detail="tenant_id required")
    
    try:
        tenant_id = UUID(tenant_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")
    
    try:
        # Get valid token (auto-refreshes if needed)
        access_token = await oauth.get_tenant_token(tenant_id)
        
        # Get token expiry info
        from ..services.database import get_db_connection
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT expires_at FROM auth.tenant_tokens WHERE tenant_id = %s",
                    (tenant_id,)
                )
                row = cur.fetchone()
                expires_at = row[0] if row else None
        
        return {
            "access_token": access_token,
            "expires_at": expires_at.isoformat() if expires_at else None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")
