"""
MS365 authentication adapter.

Provides custom TokenCredential for msgraph-sdk that integrates with
Flovify's centralized OAuth credential management in Auth service.
"""

from typing import Optional
from msgraph import GraphServiceClient
from azure.core.credentials import TokenCredential, AccessToken
import httpx
import os


class MS365AdapterError(Exception):
    """Base exception for MS365 adapter errors."""
    pass


class FlovifyTokenCredential(TokenCredential):
    """
    Custom TokenCredential that uses Flovify's Auth service for token vending.
    
    This bridges msgraph-sdk's authentication system with our centralized
    OAuth credential management in the Auth service.
    
    Note: Azure's TokenCredential requires synchronous get_token(), but our
    auth_client uses async httpx. We use httpx's sync Client here.
    """
    
    def __init__(self, credential_id: str):
        """
        Initialize credential provider.
        
        Args:
            credential_id: UUID of the credential in auth.credentials table
        """
        self.credential_id = credential_id
    
    def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        """
        Get access token from Auth service (synchronous).
        
        Args:
            scopes: OAuth scopes (ignored - uses credential's configured scopes)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            AccessToken with token and expiration timestamp
            
        Raises:
            MS365AdapterError: If token vending fails
        """
        SERVICE_SECRET = os.getenv("SERVICE_SECRET")
        AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
        
        if not SERVICE_SECRET:
            raise MS365AdapterError("SERVICE_SECRET not configured")
        
        try:
            # Use synchronous httpx client (required by TokenCredential interface)
            url = f"{AUTH_SERVICE_URL}/auth/oauth/internal/credential-token"
            headers = {
                "X-Service-Token": SERVICE_SECRET,
                "Content-Type": "application/json"
            }
            data = {"credential_id": self.credential_id}
            
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=data)
                response.raise_for_status()
                token_data = response.json()
            
            # Convert Unix timestamp for AccessToken
            expires_on = token_data["expires_at"]
            
            return AccessToken(
                token=token_data["access_token"],
                expires_on=expires_on
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MS365AdapterError(f"Credential {self.credential_id} not found or not connected")
            elif e.response.status_code == 401:
                raise MS365AdapterError("Invalid SERVICE_SECRET")
            else:
                raise MS365AdapterError(f"Auth service error: {e.response.status_code}")
        except Exception as e:
            raise MS365AdapterError(f"Unexpected error getting token: {e}")


def get_graph_client(credential_id: str) -> GraphServiceClient:
    """
    Create a Microsoft Graph API client for the given credential.
    
    Args:
        credential_id: UUID of the credential in auth.credentials table
        
    Returns:
        Configured GraphServiceClient instance
        
    Raises:
        MS365AdapterError: If client creation fails
        
    Example:
        client = get_graph_client("37b08f02-62d8-4327-aac7-f20e13b7f440")
        me = await client.me.get()
    """
    try:
        credential = FlovifyTokenCredential(credential_id)
        client = GraphServiceClient(credentials=credential)
        return client
    except Exception as e:
        raise MS365AdapterError(f"Failed to create Graph client: {e}")
