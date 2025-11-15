"""
MS365 mail adapter.

Provides normalized interfaces for email operations via Microsoft Graph API.
All functions return standardized dictionaries regardless of the underlying API structure.

Functions:
- get_message(credential_id, message_id): Fetch single message with full details
- list_messages(credential_id, folder, limit, filter_query): List messages from folder
"""

from typing import Optional, List, Dict, Any
from ._auth import get_graph_client, MS365AdapterError


async def get_message(credential_id: str, message_id: str) -> Dict[str, Any]:
    """
    Fetch a single email message from MS365.
    
    Args:
        credential_id: UUID of the credential
        message_id: MS365 message ID
        
    Returns:
        Message data as dictionary with keys:
            - id: Message ID
            - subject: Email subject
            - from: Sender info {name, address}
            - received_at: ISO timestamp
            - body_preview: First 255 chars
            - body_content: Full body (HTML or text)
            - body_type: "html" or "text"
            - has_attachments: Boolean
            - is_read: Boolean
            - importance: "normal", "high", or "low"
            
    Raises:
        MS365AdapterError: If fetch fails
        
    Example:
        msg = await get_message(cred_id, "AAMkAGI2...")
        print(msg["subject"], msg["from"]["address"])
    """
    try:
        client = get_graph_client(credential_id)
        message = await client.me.messages.by_message_id(message_id).get()
        
        if not message:
            raise MS365AdapterError(f"Message {message_id} not found")
        
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
    except MS365AdapterError:
        raise
    except Exception as e:
        raise MS365AdapterError(f"Failed to fetch message {message_id}: {e}")


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
        List of message dictionaries (same format as get_message, but without body_content)
        
    Raises:
        MS365AdapterError: If list fails
        
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
    except MS365AdapterError:
        raise
    except Exception as e:
        raise MS365AdapterError(f"Failed to list messages from {folder}: {e}")
