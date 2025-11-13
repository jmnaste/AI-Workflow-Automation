"""OAuth service for managing external provider authentication and tokens."""
import os
import base64
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import httpx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .database import get_db_connection


# Encryption setup
def _get_encryption_key() -> bytes:
    """Get or derive encryption key from environment."""
    key_str = os.environ.get("OAUTH_ENCRYPTION_KEY")
    if not key_str:
        raise ValueError("OAUTH_ENCRYPTION_KEY environment variable not set")
    
    # If it's already a valid Fernet key (44 bytes base64), use it
    try:
        key_bytes = base64.urlsafe_b64decode(key_str)
        if len(key_bytes) == 32:
            return base64.urlsafe_b64encode(key_bytes)
    except Exception:
        pass
    
    # Otherwise, derive a key from the provided string
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'flovify_oauth_salt',  # Static salt for deterministic key
        iterations=100000,
    )
    key = kdf.derive(key_str.encode())
    return base64.urlsafe_b64encode(key)


# Lazy initialization - only create Fernet when first needed
_FERNET: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or initialize Fernet cipher (lazy initialization)."""
    global _FERNET
    if _FERNET is None:
        _FERNET = Fernet(_get_encryption_key())
    return _FERNET


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token for storage."""
    if not plaintext:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored token."""
    if not ciphertext:
        return ""
    fernet = _get_fernet()
    encrypted = base64.urlsafe_b64decode(ciphertext.encode())
    decrypted = fernet.decrypt(encrypted)
    return decrypted.decode()


# MS365 OAuth configuration (DEPRECATED - for old tenant flow only)
# New credentials flow uses database-stored configuration
MS365_AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS365_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS365_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")  # DEPRECATED: Use credentials table
MS365_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")  # DEPRECATED: Use credentials table
MS365_REDIRECT_URI = os.environ.get("MICROSOFT_REDIRECT_URI", "http://localhost:8000/auth/oauth/ms365/callback")  # DEPRECATED
MS365_SCOPES = [
    "offline_access",  # Required for refresh tokens
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/User.Read",
]


# State management (in-memory for now, can be moved to Redis later)
_oauth_states: Dict[str, Dict[str, Any]] = {}


def generate_oauth_state(identifier: UUID, provider: str) -> str:
    """
    Generate and store OAuth state for CSRF protection.
    
    Args:
        identifier: Can be user_id (old tenant flow) or credential_id (new credentials flow)
        provider: Provider type (ms365, google_workspace, etc.)
    """
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "identifier": str(identifier),  # Can be user_id or credential_id
        "provider": provider,
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }
    return state


def validate_oauth_state(state: str, provider: str = None) -> Optional[UUID]:
    """
    Validate OAuth state and return identifier (user_id or credential_id) if valid.
    
    Args:
        state: OAuth state token
        provider: Provider type (optional, for backwards compatibility)
    
    Returns:
        UUID of identifier (user_id or credential_id) if valid, None otherwise
    """
    state_data = _oauth_states.get(state)
    if not state_data:
        return None
    
    # Provider check is optional for credentials flow
    if provider and state_data["provider"] != provider:
        return None
    
    if datetime.utcnow() > state_data["expires_at"]:
        _oauth_states.pop(state, None)
        return None
    
    identifier = UUID(state_data["identifier"])
    _oauth_states.pop(state, None)  # One-time use
    return identifier


def build_ms365_authorize_url(user_id: UUID) -> str:
    """Build Microsoft authorization URL with state."""
    state = generate_oauth_state(user_id, "ms365")
    
    params = {
        "client_id": MS365_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": MS365_REDIRECT_URI,
        "scope": " ".join(MS365_SCOPES),
        "state": state,
        "response_mode": "query",
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{MS365_AUTHORIZE_URL}?{query_string}"


async def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MS365_TOKEN_URL,
            data={
                "client_id": MS365_CLIENT_ID,
                "client_secret": MS365_CLIENT_SECRET,
                "code": code,
                "redirect_uri": MS365_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh an expired access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MS365_TOKEN_URL,
            data={
                "client_id": MS365_CLIENT_ID,
                "client_secret": MS365_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()


async def get_ms365_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Microsoft Graph to identify the account."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()


def store_tenant_tokens(tenant_id: UUID, tokens: Dict[str, Any], token_type: str = "delegated") -> None:
    """Store encrypted OAuth tokens for a tenant."""
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in", 3600)
    scope = tokens.get("scope", "")
    
    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    scopes = scope.split() if scope else []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth.tenant_tokens 
                    (id, tenant_id, token_type, encrypted_access_token, encrypted_refresh_token, 
                     scopes, expires_at, created_at, last_refreshed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
                ON CONFLICT (tenant_id) DO UPDATE
                SET encrypted_access_token = EXCLUDED.encrypted_access_token,
                    encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                    scopes = EXCLUDED.scopes,
                    expires_at = EXCLUDED.expires_at,
                    last_refreshed_at = now()
                """,
                (uuid4(), tenant_id, token_type, encrypted_access, encrypted_refresh, scopes, expires_at)
            )
        conn.commit()


async def get_tenant_token(tenant_id: UUID) -> str:
    """Get valid access token for tenant, refreshing if needed."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT encrypted_access_token, encrypted_refresh_token, expires_at
                FROM auth.tenant_tokens
                WHERE tenant_id = %s
                """,
                (tenant_id,)
            )
            row = cur.fetchone()
            
            if not row:
                raise ValueError(f"No tokens found for tenant {tenant_id}")
            
            encrypted_access, encrypted_refresh, expires_at = row
            
            # If token expires in more than 5 minutes, return it
            if datetime.utcnow() + timedelta(minutes=5) < expires_at:
                return decrypt_token(encrypted_access)
            
            # Token is expired or expiring soon, refresh it
            if not encrypted_refresh:
                raise ValueError(f"No refresh token available for tenant {tenant_id}")
            
            refresh_token = decrypt_token(encrypted_refresh)
            new_tokens = await refresh_access_token(refresh_token)
            
            # Store the new tokens
            store_tenant_tokens(tenant_id, new_tokens)
            
            return new_tokens["access_token"]


async def refresh_tenant_token(tenant_id: UUID) -> str:
    """Force refresh a tenant's access token."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT encrypted_refresh_token
                FROM auth.tenant_tokens
                WHERE tenant_id = %s
                """,
                (tenant_id,)
            )
            row = cur.fetchone()
            
            if not row or not row[0]:
                raise ValueError(f"No refresh token found for tenant {tenant_id}")
            
            refresh_token = decrypt_token(row[0])
            new_tokens = await refresh_access_token(refresh_token)
            
            # Store the new tokens
            store_tenant_tokens(tenant_id, new_tokens)
            
            return new_tokens["access_token"]


def create_or_update_tenant(provider: str, external_account_id: str, 
                            external_tenant_id: Optional[str], display_name: str) -> UUID:
    """Create or update a tenant record."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if tenant exists
            cur.execute(
                """
                SELECT id FROM auth.tenants
                WHERE provider = %s AND external_tenant_id = %s
                """,
                (provider, external_tenant_id or external_account_id)
            )
            row = cur.fetchone()
            
            if row:
                tenant_id = row[0]
                # Update display name
                cur.execute(
                    """
                    UPDATE auth.tenants
                    SET display_name = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (display_name, tenant_id)
                )
            else:
                # Create new tenant
                tenant_id = uuid4()
                cur.execute(
                    """
                    INSERT INTO auth.tenants 
                        (id, provider, external_tenant_id, display_name, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, now(), now())
                    """,
                    (tenant_id, provider, external_tenant_id or external_account_id, 
                     display_name, {})
                )
        conn.commit()
        return tenant_id
