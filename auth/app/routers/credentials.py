"""Credentials management routes for OAuth integrations."""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from ..services.jwt import verify_jwt
from ..services.database import get_db_connection
import os


router = APIRouter(prefix="/auth/credentials", tags=["credentials"])


# Request/Response Models
class CreateCredentialRequest(BaseModel):
    """Request to create a new OAuth credential."""
    name: str = Field(..., description="Unique credential slug (e.g., 'acme-ms365')")
    display_name: str = Field(..., description="Human-readable name (e.g., 'Acme Corp MS365')")
    provider: str = Field(..., description="Provider type: 'ms365' or 'google_workspace'")
    client_id: str = Field(..., description="OAuth app client ID")
    client_secret: str = Field(..., description="OAuth app client secret (will be encrypted)")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    tenant_id: Optional[str] = Field(None, description="Azure AD Tenant ID for MS365 single-tenant apps (GUID format)")
    authorization_url: Optional[str] = Field(None, description="Custom authorization URL (uses provider default if not specified)")
    token_url: Optional[str] = Field(None, description="Custom token URL (uses provider default if not specified)")
    scopes: Optional[List[str]] = Field(None, description="OAuth scopes (uses provider defaults if not specified)")


class UpdateCredentialRequest(BaseModel):
    """Request to update an existing credential."""
    display_name: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    tenant_id: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    scopes: Optional[List[str]] = None


class CredentialResponse(BaseModel):
    """Credential information (without secrets)."""
    id: str
    name: str
    display_name: str
    provider: str
    client_id: str
    redirect_uri: str
    tenant_id: Optional[str]
    authorization_url: str
    token_url: str
    scopes: List[str]
    connected_email: Optional[str]
    external_account_id: Optional[str]
    connected_display_name: Optional[str]
    status: str
    error_message: Optional[str]
    last_connected_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime


# Helper functions
def verify_admin(authorization: str = Header(..., alias="Authorization")) -> dict:
    """Verify JWT and ensure user has admin role."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = verify_jwt(token)
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_provider_defaults(provider: str, tenant_id: Optional[str] = None) -> dict:
    """
    Get default OAuth URLs and scopes for a provider.
    
    Args:
        provider: Provider type ('ms365' or 'google_workspace')
        tenant_id: Azure AD Tenant ID for MS365 single-tenant apps (optional)
    
    Returns:
        Dict with authorization_url, token_url, and scopes
    """
    if provider == "ms365":
        # Use tenant-specific endpoint if tenant_id provided, otherwise use /common
        tenant_segment = tenant_id if tenant_id else "common"
        return {
            "authorization_url": f"https://login.microsoftonline.com/{tenant_segment}/oauth2/v2.0/authorize",
            "token_url": f"https://login.microsoftonline.com/{tenant_segment}/oauth2/v2.0/token",
            "scopes": [
                "offline_access",
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Mail.Send",
                "https://graph.microsoft.com/User.Read",
            ]
        }
    elif provider == "google_workspace":
        return {
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/userinfo.email",
            ]
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


# Endpoints
@router.get("/", response_model=List[CredentialResponse])
async def list_credentials(admin_payload: dict = Depends(verify_admin)):
    """
    List all credentials (admin only).
    
    Returns all configured OAuth credentials with their connection status.
    Client secrets are never returned.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id, c.name, c.display_name, c.provider, c.client_id,
                    c.redirect_uri, c.tenant_id, c.authorization_url, c.token_url, c.scopes,
                    c.connected_email, c.external_account_id, c.connected_display_name,
                    c.status, c.error_message, c.last_connected_at,
                    c.created_at, u.email as created_by_email, c.updated_at
                FROM auth.credentials c
                LEFT JOIN auth.users u ON c.created_by = u.id
                ORDER BY c.created_at DESC
            """)
            
            rows = cur.fetchall()
            
            return [
                CredentialResponse(
                    id=str(row['id']),
                    name=row['name'],
                    display_name=row['display_name'],
                    provider=row['provider'],
                    client_id=row['client_id'],
                    redirect_uri=row['redirect_uri'],
                    tenant_id=row['tenant_id'],
                    authorization_url=row['authorization_url'],
                    token_url=row['token_url'],
                    scopes=row['scopes'],
                    connected_email=row['connected_email'],
                    external_account_id=row['external_account_id'],
                    connected_display_name=row['connected_display_name'],
                    status=row['status'],
                    error_message=row['error_message'],
                    last_connected_at=row['last_connected_at'],
                    created_at=row['created_at'],
                    created_by=row['created_by_email'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]


@router.post("/", response_model=CredentialResponse, status_code=201)
async def create_credential(
    request: CreateCredentialRequest,
    admin_payload: dict = Depends(verify_admin)
):
    """
    Create a new OAuth credential (admin only).
    
    Creates credential in 'pending' status. Use OAuth flow to connect.
    """
    from ..services.oauth import encrypt_token
    
    # Get provider defaults (pass tenant_id for MS365 single-tenant)
    defaults = get_provider_defaults(request.provider, request.tenant_id)
    
    # Use provided values or defaults
    authorization_url = request.authorization_url or defaults["authorization_url"]
    token_url = request.token_url or defaults["token_url"]
    scopes = request.scopes or defaults["scopes"]
    
    # Encrypt client secret
    encrypted_secret = encrypt_token(request.client_secret)
    
    user_id = UUID(admin_payload["userId"])
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO auth.credentials (
                        name, display_name, provider, client_id, encrypted_client_secret,
                        redirect_uri, tenant_id, authorization_url, token_url, scopes,
                        status, created_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s
                    )
                    RETURNING 
                        id, name, display_name, provider, client_id,
                        redirect_uri, tenant_id, authorization_url, token_url, scopes,
                        connected_email, external_account_id, connected_display_name,
                        status, error_message, last_connected_at,
                        created_at, created_by, updated_at
                """, (
                    request.name, request.display_name, request.provider,
                    request.client_id, encrypted_secret, request.redirect_uri,
                    request.tenant_id, authorization_url, token_url, scopes, user_id
                ))
                
                row = cur.fetchone()
                conn.commit()
                
                return CredentialResponse(
                    id=str(row['id']),
                    name=row['name'],
                    display_name=row['display_name'],
                    provider=row['provider'],
                    client_id=row['client_id'],
                    redirect_uri=row['redirect_uri'],
                    tenant_id=row['tenant_id'],
                    authorization_url=row['authorization_url'],
                    token_url=row['token_url'],
                    scopes=row['scopes'],
                    connected_email=row['connected_email'],
                    external_account_id=row['external_account_id'],
                    connected_display_name=row['connected_display_name'],
                    status=row['status'],
                    error_message=row['error_message'],
                    last_connected_at=row['last_connected_at'],
                    created_at=row['created_at'],
                    created_by=None,  # Don't expose creator ID
                    updated_at=row['updated_at']
                )
                
            except Exception as e:
                conn.rollback()
                # Log the full error for debugging
                import traceback
                print(f"ERROR creating credential: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                # Check for unique constraint violations
                if "unique" in str(e).lower():
                    if "name" in str(e).lower():
                        raise HTTPException(status_code=409, detail=f"Credential name '{request.name}' already exists")
                    elif "provider" in str(e).lower() and "client_id" in str(e).lower():
                        raise HTTPException(status_code=409, detail="A credential with this provider and client_id already exists")
                raise HTTPException(status_code=500, detail=f"Failed to create credential: {str(e)}")


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: UUID,
    admin_payload: dict = Depends(verify_admin)
):
    """Get a specific credential by ID (admin only)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id, c.name, c.display_name, c.provider, c.client_id,
                    c.redirect_uri, c.tenant_id, c.authorization_url, c.token_url, c.scopes,
                    c.connected_email, c.external_account_id, c.connected_display_name,
                    c.status, c.error_message, c.last_connected_at,
                    c.created_at, u.email as created_by_email, c.updated_at
                FROM auth.credentials c
                LEFT JOIN auth.users u ON c.created_by = u.id
                WHERE c.id = %s
            """, (credential_id,))
            
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Credential not found")
            
            return CredentialResponse(
                id=str(row['id']),
                name=row['name'],
                display_name=row['display_name'],
                provider=row['provider'],
                client_id=row['client_id'],
                redirect_uri=row['redirect_uri'],
                tenant_id=row['tenant_id'],
                authorization_url=row['authorization_url'],
                token_url=row['token_url'],
                scopes=row['scopes'],
                connected_email=row['connected_email'],
                external_account_id=row['external_account_id'],
                connected_display_name=row['connected_display_name'],
                status=row['status'],
                error_message=row['error_message'],
                last_connected_at=row['last_connected_at'],
                created_at=row['created_at'],
                created_by=row['created_by_email'],
                updated_at=row['updated_at']
            )


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: UUID,
    request: UpdateCredentialRequest,
    admin_payload: dict = Depends(verify_admin)
):
    """
    Update a credential (admin only).
    
    Can update display name, OAuth config. Updating OAuth config will reset status to 'pending'.
    """
    from ..services.oauth import encrypt_token
    
    # Build dynamic UPDATE query based on provided fields
    updates = []
    params = []
    
    if request.display_name is not None:
        updates.append("display_name = %s")
        params.append(request.display_name)
    
    if request.client_id is not None:
        updates.append("client_id = %s")
        params.append(request.client_id)
        updates.append("status = 'pending'")  # Reset status when OAuth config changes
    
    if request.client_secret is not None:
        updates.append("encrypted_client_secret = %s")
        params.append(encrypt_token(request.client_secret))
        updates.append("status = 'pending'")
    
    if request.redirect_uri is not None:
        updates.append("redirect_uri = %s")
        params.append(request.redirect_uri)
        updates.append("status = 'pending'")
    
    if request.tenant_id is not None:
        updates.append("tenant_id = %s")
        params.append(request.tenant_id)
        updates.append("status = 'pending'")  # Reset status when tenant changes
    
    if request.authorization_url is not None:
        updates.append("authorization_url = %s")
        params.append(request.authorization_url)
    
    if request.token_url is not None:
        updates.append("token_url = %s")
        params.append(request.token_url)
    
    if request.scopes is not None:
        updates.append("scopes = %s")
        params.append(request.scopes)
        updates.append("status = 'pending'")
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = now()")
    params.append(credential_id)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                query = f"""
                    UPDATE auth.credentials 
                    SET {', '.join(updates)}
                    WHERE id = %s
                    RETURNING 
                        id, name, display_name, provider, client_id,
                        redirect_uri, tenant_id, authorization_url, token_url, scopes,
                        connected_email, external_account_id, connected_display_name,
                        status, error_message, last_connected_at,
                        created_at, created_by, updated_at
                """
                
                cur.execute(query, params)
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Credential not found")
                
                conn.commit()
                
                return CredentialResponse(
                    id=str(row['id']),
                    name=row['name'],
                    display_name=row['display_name'],
                    provider=row['provider'],
                    client_id=row['client_id'],
                    redirect_uri=row['redirect_uri'],
                    tenant_id=row['tenant_id'],
                    authorization_url=row['authorization_url'],
                    token_url=row['token_url'],
                    scopes=row['scopes'],
                    connected_email=row['connected_email'],
                    external_account_id=row['external_account_id'],
                    connected_display_name=row['connected_display_name'],
                    status=row['status'],
                    error_message=row['error_message'],
                    last_connected_at=row['last_connected_at'],
                    created_at=row['created_at'],
                    created_by=None,
                    updated_at=row['updated_at']
                )
                
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to update credential: {str(e)}")


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: UUID,
    admin_payload: dict = Depends(verify_admin)
):
    """
    Delete a credential (admin only).
    
    Also deletes associated tokens (CASCADE).
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auth.credentials WHERE id = %s", (credential_id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Credential not found")
            
            conn.commit()
    
    return None
