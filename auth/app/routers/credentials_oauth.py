"""OAuth flow for credentials (uses database config instead of environment variables)."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from typing import Dict, Any
from uuid import UUID
import httpx
from ..services.oauth import (
    generate_oauth_state,
    validate_oauth_state,
    decrypt_token,
    encrypt_token
)
from ..services.database import get_db_connection


router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


@router.get("/authorize")
async def authorize_oauth(credential_id: str, request: Request) -> Dict[str, str]:
    """
    Get OAuth authorization URL for a specific credential.
    
    Query params:
    - credential_id: UUID of the credential to connect
    
    Returns JSON with authorization_url that frontend should redirect to.
    """
    try:
        cred_uuid = UUID(credential_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid credential_id format")
    
    # Get credential from database
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id, provider, client_id, redirect_uri, 
                    authorization_url, scopes
                FROM auth.credentials
                WHERE id = %s
            """, (cred_uuid,))
            
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Credential not found")
            
            credential = {
                "id": str(row['id']),
                "provider": row['provider'],
                "client_id": row['client_id'],
                "redirect_uri": row['redirect_uri'],
                "authorization_url": row['authorization_url'],
                "scopes": row['scopes']
            }
    
    # Generate state for CSRF protection
    state = generate_oauth_state(cred_uuid, credential["provider"])
    
    # Build authorization URL
    scopes_str = " ".join(credential["scopes"])
    
    params = {
        "client_id": credential["client_id"],
        "response_type": "code",
        "redirect_uri": credential["redirect_uri"],
        "scope": scopes_str,
        "state": state,
        "response_mode": "query"
    }
    
    # Add provider-specific parameters
    if credential["provider"] == "ms365":
        params["prompt"] = "select_account"
    elif credential["provider"] == "google_workspace":
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    
    # Build query string
    query_string = "&".join([f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items()])
    auth_url = f"{credential['authorization_url']}?{query_string}"
    
    # Return JSON with authorization URL for frontend to redirect to
    return {
        "authorization_url": auth_url,
        "provider": credential["provider"]
    }


@router.get("/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None, error_description: str = None):
    """
    Handle OAuth callback from provider.
    
    Exchanges authorization code for tokens, stores encrypted tokens,
    updates credential status to 'connected'.
    """
    # Check for OAuth errors
    if error:
        error_msg = error_description or error
        return RedirectResponse(url=f"/admin/credentials?error={error_msg}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    # Validate state and get credential_id
    credential_id = validate_oauth_state(state)
    if not credential_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    try:
        # Get credential details from database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, provider, client_id, encrypted_client_secret,
                        redirect_uri, token_url, scopes
                    FROM auth.credentials
                    WHERE id = %s
                """, (credential_id,))
                
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Credential not found")
                
                credential = {
                    "id": str(row['id']),
                    "provider": row['provider'],
                    "client_id": row['client_id'],
                    "client_secret": decrypt_token(row['encrypted_client_secret']),
                    "redirect_uri": row['redirect_uri'],
                    "token_url": row['token_url'],
                    "scopes": row['scopes']
                }
        
        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(
            code=code,
            client_id=credential["client_id"],
            client_secret=credential["client_secret"],
            redirect_uri=credential["redirect_uri"],
            token_url=credential["token_url"]
        )
        
        # Get user info from provider
        if credential["provider"] == "ms365":
            user_info = await get_ms365_user_info(tokens["access_token"])
            external_account_id = user_info.get("id")
            email = user_info.get("userPrincipalName") or user_info.get("mail")
            display_name = user_info.get("displayName")
        elif credential["provider"] == "google_workspace":
            user_info = await get_google_user_info(tokens["access_token"])
            external_account_id = user_info.get("sub")
            email = user_info.get("email")
            display_name = user_info.get("name")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {credential['provider']}")
        
        # Store tokens and update credential status
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Update credential with connection info
                cur.execute("""
                    UPDATE auth.credentials
                    SET 
                        connected_email = %s,
                        external_account_id = %s,
                        connected_display_name = %s,
                        status = 'connected',
                        error_message = NULL,
                        last_connected_at = now(),
                        updated_at = now()
                    WHERE id = %s
                """, (email, external_account_id, display_name, credential_id))
                
                # Store or update tokens
                cur.execute("""
                    INSERT INTO auth.credential_tokens (
                        credential_id, token_type, encrypted_access_token,
                        encrypted_refresh_token, scopes, expires_at
                    ) VALUES (
                        %s, 'delegated', %s, %s, %s, 
                        now() + interval '1 hour' * %s
                    )
                    ON CONFLICT (credential_id) DO UPDATE
                    SET 
                        encrypted_access_token = EXCLUDED.encrypted_access_token,
                        encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                        scopes = EXCLUDED.scopes,
                        expires_at = EXCLUDED.expires_at,
                        last_refreshed_at = now()
                """, (
                    credential_id,
                    encrypt_token(tokens["access_token"]),
                    encrypt_token(tokens.get("refresh_token", "")),
                    credential["scopes"],
                    tokens.get("expires_in", 3600) / 3600.0  # Convert seconds to hours
                ))
                
                conn.commit()
        
        # Redirect to UI success page
        return RedirectResponse(url="/admin/credentials?success=true")
        
    except Exception as e:
        # Update credential status to error
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE auth.credentials
                        SET status = 'error', error_message = %s, updated_at = now()
                        WHERE id = %s
                    """, (str(e), credential_id))
                    conn.commit()
        except:
            pass  # Ignore errors in error handling
        
        # Redirect to UI with error
        return RedirectResponse(url=f"/admin/credentials?error={str(e)}")


# Internal endpoint for API service to request tokens
@router.post("/internal/credential-token")
async def get_credential_token_internal(request: Request) -> Dict[str, Any]:
    """
    Internal endpoint for API service to request credential access token.
    
    Requires X-Service-Token header for authentication.
    Returns valid access token, refreshing if needed.
    
    Request body can identify credential by:
    - credential_id (UUID)
    - credential_name (string)
    - email (string)
    - external_account_id (string)
    """
    import os
    from datetime import datetime, timezone
    
    # Validate service token
    service_token = request.headers.get("X-Service-Token")
    expected_token = os.environ.get("SERVICE_SECRET")
    
    if not service_token or service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    
    # Get credential identifier from request body
    body = await request.json()
    credential_id = body.get("credential_id")
    credential_name = body.get("credential_name")
    email = body.get("email")
    external_account_id = body.get("external_account_id")
    
    if not any([credential_id, credential_name, email, external_account_id]):
        raise HTTPException(
            status_code=400, 
            detail="Must provide one of: credential_id, credential_name, email, or external_account_id"
        )
    
    # Build query based on provided identifier
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if credential_id:
                try:
                    cred_uuid = UUID(credential_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid credential_id format")
                
                cur.execute("""
                    SELECT c.id, c.provider, c.client_id, c.encrypted_client_secret,
                           c.token_url, ct.encrypted_access_token, ct.encrypted_refresh_token,
                           ct.expires_at, c.scopes
                    FROM auth.credentials c
                    LEFT JOIN auth.credential_tokens ct ON c.id = ct.credential_id
                    WHERE c.id = %s AND c.status = 'connected'
                """, (cred_uuid,))
            
            elif credential_name:
                cur.execute("""
                    SELECT c.id, c.provider, c.client_id, c.encrypted_client_secret,
                           c.token_url, ct.encrypted_access_token, ct.encrypted_refresh_token,
                           ct.expires_at, c.scopes
                    FROM auth.credentials c
                    LEFT JOIN auth.credential_tokens ct ON c.id = ct.credential_id
                    WHERE c.name = %s AND c.status = 'connected'
                """, (credential_name,))
            
            elif email:
                cur.execute("""
                    SELECT c.id, c.provider, c.client_id, c.encrypted_client_secret,
                           c.token_url, ct.encrypted_access_token, ct.encrypted_refresh_token,
                           ct.expires_at, c.scopes
                    FROM auth.credentials c
                    LEFT JOIN auth.credential_tokens ct ON c.id = ct.credential_id
                    WHERE c.connected_email = %s AND c.status = 'connected'
                """, (email,))
            
            elif external_account_id:
                cur.execute("""
                    SELECT c.id, c.provider, c.client_id, c.encrypted_client_secret,
                           c.token_url, ct.encrypted_access_token, ct.encrypted_refresh_token,
                           ct.expires_at, c.scopes
                    FROM auth.credentials c
                    LEFT JOIN auth.credential_tokens ct ON c.id = ct.credential_id
                    WHERE c.external_account_id = %s AND c.status = 'connected'
                """, (external_account_id,))
            
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Connected credential not found")
            
            cred_id = row['id']
            provider = row['provider']
            client_id = row['client_id']
            client_secret = decrypt_token(row['encrypted_client_secret'])
            token_url = row['token_url']
            encrypted_access = row['encrypted_access_token']
            encrypted_refresh = row['encrypted_refresh_token']
            expires_at = row['expires_at']
            scopes = row['scopes']
    
    # Check if we have tokens
    if not encrypted_access:
        raise HTTPException(status_code=404, detail="No tokens found for this credential")
    
    # Decrypt access token
    access_token = decrypt_token(encrypted_access)
    
    # Check if token is expired (with 5-minute buffer)
    now = datetime.now(timezone.utc)
    if expires_at and (expires_at - now).total_seconds() < 300:
        # Token expired or expiring soon, refresh it
        if not encrypted_refresh:
            raise HTTPException(status_code=401, detail="Token expired and no refresh token available")
        
        refresh_token = decrypt_token(encrypted_refresh)
        
        # Refresh the token
        new_tokens = await refresh_access_token(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url
        )
        
        # Update stored tokens
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE auth.credential_tokens
                    SET 
                        encrypted_access_token = %s,
                        expires_at = now() + interval '1 hour' * %s,
                        last_refreshed_at = now()
                    WHERE credential_id = %s
                    RETURNING expires_at
                """, (
                    encrypt_token(new_tokens["access_token"]),
                    new_tokens.get("expires_in", 3600) / 3600.0,
                    cred_id
                ))
                
                row = cur.fetchone()
                # psycopg3 Row object - access by column name or convert to tuple
                new_expires_at = row['expires_at'] if row else None
                conn.commit()
        
        access_token = new_tokens["access_token"]
        expires_at = new_expires_at
    
    # Convert expires_at to Unix timestamp for easier client handling
    expires_timestamp = None
    if expires_at:
        if hasattr(expires_at, 'timestamp'):
            expires_timestamp = int(expires_at.timestamp())
        else:
            # If it's already a timestamp, use it
            expires_timestamp = int(expires_at) if isinstance(expires_at, (int, float)) else None
    
    return {
        "access_token": access_token,
        "expires_at": expires_timestamp,
        "token_type": "Bearer",
        "credential_id": str(cred_id),
        "provider": provider
    }


# Helper functions
async def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    token_url: str
) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Token exchange failed: {response.text}"
            )
        
        return response.json()


async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
    token_url: str
) -> Dict[str, Any]:
    """Refresh an expired access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Token refresh failed: {response.text}"
            )
        
        return response.json()


async def get_ms365_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Microsoft Graph API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to get user info: {response.text}"
            )
        
        return response.json()


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Google API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to get user info: {response.text}"
            )
        
        return response.json()
