"""
Microsoft 365 Graph API service layer.

Provides functions to interact with MS365 resources using OAuth tokens
vended by the Auth service. Uses msgraph-sdk for Graph API calls.
"""

from typing import Optional, List, Dict, Any
from msgraph import GraphServiceClient
from azure.core.credentials import TokenCredential, AccessToken
from datetime import datetime, timezone
import httpx

from .auth_client import get_credential_token, AuthClientError


class MS365ServiceError(Exception):
    """Base exception for MS365 service errors."""
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
            MS365ServiceError: If token vending fails
        """
        import os
        
        SERVICE_SECRET = os.getenv("SERVICE_SECRET")
        AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
        
        if not SERVICE_SECRET:
            raise MS365ServiceError("SERVICE_SECRET not configured")
        
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
                raise MS365ServiceError(f"Credential {self.credential_id} not found or not connected")
            elif e.response.status_code == 401:
                raise MS365ServiceError("Invalid SERVICE_SECRET")
            else:
                raise MS365ServiceError(f"Auth service error: {e.response.status_code}")
        except AuthClientError as e:
            raise MS365ServiceError(f"Failed to get token for credential {self.credential_id}: {e}")
        except Exception as e:
            raise MS365ServiceError(f"Unexpected error getting token: {e}")


def get_graph_client(credential_id: str) -> GraphServiceClient:
    """
    Create a Microsoft Graph API client for the given credential.
    
    Args:
        credential_id: UUID of the credential in auth.credentials table
        
    Returns:
        Configured GraphServiceClient instance
        
    Raises:
        MS365ServiceError: If client creation fails
        
    Example:
        client = get_graph_client("37b08f02-62d8-4327-aac7-f20e13b7f440")
        me = await client.me.get()
    """
    try:
        credential = FlovifyTokenCredential(credential_id)
        client = GraphServiceClient(credentials=credential)
        return client
    except Exception as e:
        raise MS365ServiceError(f"Failed to create Graph client: {e}")


async def fetch_message(credential_id: str, message_id: str) -> Dict[str, Any]:
    """
    Fetch a single email message from MS365.
    
    Args:
        credential_id: UUID of the credential
        message_id: MS365 message ID
        
    Returns:
        Message data as dictionary with keys:
            - id: Message ID
            - subject: Email subject
            - from: Sender info
            - received_at: ISO timestamp
            - body_preview: First 255 chars
            - body_content: Full body (HTML or text)
            - has_attachments: Boolean
            
    Raises:
        MS365ServiceError: If fetch fails
        
    Example:
        msg = await fetch_message(cred_id, "AAMkAGI2...")
    """
    try:
        client = get_graph_client(credential_id)
        message = await client.me.messages.by_message_id(message_id).get()
        
        if not message:
            raise MS365ServiceError(f"Message {message_id} not found")
        
        # Normalize to our standard format
        return {
            "id": message.id,
            "subject": message.subject or "",
            "from": {
                "name": message.from_.email_address.name if message.from_ else None,
                "address": message.from_.email_address.address if message.from_ else None
            },
            "received_at": message.received_date_time.isoformat() if message.received_date_time else None,
            "body_preview": message.body_preview or "",
            "body_content": message.body.content if message.body else "",
            "body_type": message.body.content_type.value if message.body else "text",
            "has_attachments": message.has_attachments or False,
            "is_read": message.is_read or False,
            "importance": message.importance.value if message.importance else "normal"
        }
    except MS365ServiceError:
        raise
    except Exception as e:
        raise MS365ServiceError(f"Failed to fetch message {message_id}: {e}")


async def list_messages(
    credential_id: str,
    folder: str = "inbox",
    limit: int = 50,
    filter_query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List email messages from a folder.
    
    Args:
        credential_id: UUID of the credential
        folder: Folder name (inbox, sentitems, drafts, etc.)
        limit: Maximum messages to return (default 50, max 100)
        filter_query: OData filter query (e.g., "isRead eq false")
        
    Returns:
        List of message dictionaries (same format as fetch_message)
        
    Raises:
        MS365ServiceError: If list fails
        
    Example:
        messages = await list_messages(cred_id, folder="inbox", limit=10)
        unread = await list_messages(cred_id, filter_query="isRead eq false")
    """
    try:
        client = get_graph_client(credential_id)
        
        # Build query parameters using msgraph SDK's query parameters class
        from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
        
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=min(limit, 100),
            select=["id", "subject", "from", "receivedDateTime", "bodyPreview", 
                   "hasAttachments", "isRead", "importance"]
        )
        
        if filter_query:
            query_params.filter = filter_query
        
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        
        # Get messages from folder
        if folder.lower() == "inbox":
            messages_response = await client.me.mail_folders.by_mail_folder_id("inbox").messages.get(
                request_configuration=request_config
            )
        else:
            # Try to find folder by name
            messages_response = await client.me.mail_folders.by_mail_folder_id(folder).messages.get(
                request_configuration=request_config
            )
        
        if not messages_response or not messages_response.value:
            return []
        
        # Normalize messages
        result = []
        for msg in messages_response.value:
            result.append({
                "id": msg.id,
                "subject": msg.subject or "",
                "from": {
                    "name": msg.from_.email_address.name if msg.from_ else None,
                    "address": msg.from_.email_address.address if msg.from_ else None
                },
                "received_at": msg.received_date_time.isoformat() if msg.received_date_time else None,
                "body_preview": msg.body_preview or "",
                "has_attachments": msg.has_attachments or False,
                "is_read": msg.is_read or False,
                "importance": msg.importance.value if msg.importance else "normal"
            })
        
        return result
    except MS365ServiceError:
        raise
    except Exception as e:
        raise MS365ServiceError(f"Failed to list messages from {folder}: {e}")


async def create_subscription(
    credential_id: str,
    resource: str,
    change_types: List[str],
    notification_url: str,
    expiration_hours: int = 72
) -> Dict[str, Any]:
    """
    Create a webhook subscription for MS365 notifications.
    
    Args:
        credential_id: UUID of the credential
        resource: Resource path (e.g., "me/mailFolders('inbox')/messages")
        change_types: List of change types (created, updated, deleted)
        notification_url: HTTPS URL to receive notifications
        expiration_hours: Subscription lifetime in hours (default 72, max 4230)
        
    Returns:
        Subscription data with keys:
            - id: Subscription ID
            - resource: Resource path
            - change_types: List of change types
            - notification_url: Callback URL
            - expires_at: ISO timestamp
            
    Raises:
        MS365ServiceError: If subscription creation fails
        
    Example:
        sub = await create_subscription(
            cred_id,
            resource="me/mailFolders('inbox')/messages",
            change_types=["created"],
            notification_url="https://webhooks.flovify.ca/webhooks/ms365/webhook"
        )
    """
    try:
        client = get_graph_client(credential_id)
        
        # Calculate expiration (max 4230 hours = ~6 months for mail)
        from datetime import timedelta
        expiration_hours = min(expiration_hours, 4230)
        expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
        
        # Create subscription object
        from msgraph.generated.models.subscription import Subscription
        subscription = Subscription()
        subscription.change_type = ",".join(change_types)
        subscription.notification_url = notification_url
        subscription.resource = resource
        subscription.expiration_date_time = expiration
        
        # Optional: Add client state for validation
        # subscription.client_state = "flovify-webhook-secret"
        
        # Create subscription
        result = await client.subscriptions.post(subscription)
        
        if not result:
            raise MS365ServiceError("Subscription creation returned empty result")
        
        return {
            "id": result.id,
            "resource": result.resource,
            "change_types": result.change_type.split(","),
            "notification_url": result.notification_url,
            "expires_at": result.expiration_date_time.isoformat() if result.expiration_date_time else None,
            "client_state": result.client_state
        }
    except MS365ServiceError:
        raise
    except Exception as e:
        raise MS365ServiceError(f"Failed to create subscription: {e}")


async def renew_subscription(credential_id: str, subscription_id: str, expiration_hours: int = 72) -> Dict[str, Any]:
    """
    Renew an existing webhook subscription.
    
    Args:
        credential_id: UUID of the credential
        subscription_id: MS365 subscription ID
        expiration_hours: New lifetime in hours (default 72, max 4230)
        
    Returns:
        Updated subscription data
        
    Raises:
        MS365ServiceError: If renewal fails
        
    Example:
        updated = await renew_subscription(cred_id, sub_id, expiration_hours=72)
    """
    try:
        client = get_graph_client(credential_id)
        
        from datetime import timedelta
        expiration_hours = min(expiration_hours, 4230)
        expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
        
        # Update subscription
        from msgraph.generated.models.subscription import Subscription
        subscription = Subscription()
        subscription.expiration_date_time = expiration
        
        result = await client.subscriptions.by_subscription_id(subscription_id).patch(subscription)
        
        if not result:
            raise MS365ServiceError(f"Subscription {subscription_id} not found")
        
        return {
            "id": result.id,
            "expires_at": result.expiration_date_time.isoformat() if result.expiration_date_time else None
        }
    except MS365ServiceError:
        raise
    except Exception as e:
        raise MS365ServiceError(f"Failed to renew subscription {subscription_id}: {e}")


async def delete_subscription(credential_id: str, subscription_id: str) -> None:
    """
    Delete a webhook subscription.
    
    Args:
        credential_id: UUID of the credential
        subscription_id: MS365 subscription ID
        
    Raises:
        MS365ServiceError: If deletion fails
        
    Example:
        await delete_subscription(cred_id, sub_id)
    """
    try:
        client = get_graph_client(credential_id)
        await client.subscriptions.by_subscription_id(subscription_id).delete()
    except Exception as e:
        raise MS365ServiceError(f"Failed to delete subscription {subscription_id}: {e}")
