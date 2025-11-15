"""
MS365 Webhook Subscription Management Routes

Handles CRUD operations for MS365 webhook subscriptions.
Subscriptions are stored in api.webhook_subscriptions table.
"""

from fastapi import APIRouter, HTTPException, Body, Request, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid
import json

from ..services.ms365_service import (
    create_subscription,
    renew_subscription,
    delete_subscription,
    MS365ServiceError
)
from ..services.database import get_db_connection

# Note: Mail operations now in adapters.ms365.mail
# Subscription operations remain in services until Phase 2


router = APIRouter(prefix="/webhooks/ms365", tags=["MS365 Webhooks"])


class CreateSubscriptionRequest(BaseModel):
    """Request to create a new MS365 webhook subscription"""
    credential_id: str = Field(..., description="UUID of the credential")
    resource: str = Field(
        ..., 
        description="MS365 resource path",
        examples=["me/mailFolders('inbox')/messages", "me/messages"]
    )
    change_types: List[str] = Field(
        ...,
        description="Types of changes to monitor",
        examples=[["created"], ["created", "updated"]]
    )
    notification_url: str = Field(
        ...,
        description="HTTPS URL to receive notifications",
        examples=["https://webhooks.flovify.ca/webhooks/ms365/webhook"]
    )
    expiration_hours: int = Field(
        default=72,
        description="Subscription lifetime in hours (max 4230 for mail)",
        ge=1,
        le=4230
    )


class SubscriptionResponse(BaseModel):
    """Response with subscription details"""
    id: str
    credential_id: str
    provider: str
    external_subscription_id: str
    resource_path: str
    notification_url: str
    change_types: List[str]
    status: str
    expires_at: Optional[datetime]
    created_at: datetime
    last_notification_at: Optional[datetime]


class RenewSubscriptionRequest(BaseModel):
    """Request to renew an existing subscription"""
    expiration_hours: int = Field(
        default=72,
        description="New lifetime in hours",
        ge=1,
        le=4230
    )


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def create_webhook_subscription(request: CreateSubscriptionRequest):
    """
    Create a new MS365 webhook subscription.
    
    This will:
    1. Call MS365 Graph API to create the subscription
    2. Store subscription details in api.webhook_subscriptions table
    3. Return subscription information
    
    Requires:
    - Credential must be connected (have valid OAuth tokens)
    - notification_url must be HTTPS
    - notification_url must be publicly accessible for MS365 to validate
    
    Example:
        POST /webhooks/ms365/subscriptions
        {
            "credential_id": "37b08f02-62d8-4327-aac7-f20e13b7f440",
            "resource": "me/mailFolders('inbox')/messages",
            "change_types": ["created"],
            "notification_url": "https://webhooks.flovify.ca/webhooks/ms365/webhook",
            "expiration_hours": 72
        }
    """
    try:
        # Create subscription via MS365 Graph API
        sub_result = await create_subscription(
            credential_id=request.credential_id,
            resource=request.resource,
            change_types=request.change_types,
            notification_url=request.notification_url,
            expiration_hours=request.expiration_hours
        )
        
        # Store in database
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Parse expires_at from ISO string to datetime
                expires_at = datetime.fromisoformat(sub_result["expires_at"].replace('Z', '+00:00')) if sub_result.get("expires_at") else None
                
                cur.execute("""
                    INSERT INTO api.webhook_subscriptions (
                        credential_id, provider, external_subscription_id,
                        resource_path, notification_url, change_types,
                        status, expires_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    request.credential_id,
                    'ms365',
                    sub_result["id"],
                    sub_result["resource"],
                    sub_result["notification_url"],
                    sub_result["change_types"],
                    'active',
                    expires_at
                ))
                
                row = cur.fetchone()
                subscription_id = row[0]
                created_at = row[1]
                
                conn.commit()
                
                return SubscriptionResponse(
                    id=str(subscription_id),
                    credential_id=request.credential_id,
                    provider='ms365',
                    external_subscription_id=sub_result["id"],
                    resource_path=sub_result["resource"],
                    notification_url=sub_result["notification_url"],
                    change_types=sub_result["change_types"],
                    status='active',
                    expires_at=expires_at,
                    created_at=created_at,
                    last_notification_at=None
                )
        finally:
            conn.close()
            
    except MS365ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@router.get("/subscriptions/{credential_id}", response_model=List[SubscriptionResponse])
async def list_subscriptions(credential_id: str, status: Optional[str] = None):
    """
    List webhook subscriptions for a credential.
    
    Args:
        credential_id: UUID of the credential
        status: Optional filter by status (active, expired, error)
        
    Returns:
        List of subscriptions
        
    Examples:
        GET /webhooks/ms365/subscriptions/37b08f02-62d8-4327-aac7-f20e13b7f440
        GET /webhooks/ms365/subscriptions/37b08f02-62d8-4327-aac7-f20e13b7f440?status=active
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                if status:
                    cur.execute("""
                        SELECT id, credential_id, provider, external_subscription_id,
                               resource_path, notification_url, change_types, status,
                               expires_at, created_at, last_notification_at
                        FROM api.webhook_subscriptions
                        WHERE credential_id = %s AND status = %s
                        ORDER BY created_at DESC
                    """, (credential_id, status))
                else:
                    cur.execute("""
                        SELECT id, credential_id, provider, external_subscription_id,
                               resource_path, notification_url, change_types, status,
                               expires_at, created_at, last_notification_at
                        FROM api.webhook_subscriptions
                        WHERE credential_id = %s
                        ORDER BY created_at DESC
                    """, (credential_id,))
                
                rows = cur.fetchall()
                
                subscriptions = []
                for row in rows:
                    subscriptions.append(SubscriptionResponse(
                        id=str(row[0]),
                        credential_id=str(row[1]),
                        provider=row[2],
                        external_subscription_id=row[3],
                        resource_path=row[4],
                        notification_url=row[5],
                        change_types=row[6],
                        status=row[7],
                        expires_at=row[8],
                        created_at=row[9],
                        last_notification_at=row[10]
                    ))
                
                return subscriptions
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list subscriptions: {str(e)}")


@router.patch("/subscriptions/{subscription_id}/renew")
async def renew_webhook_subscription(
    subscription_id: str,
    request: RenewSubscriptionRequest
):
    """
    Renew an existing webhook subscription.
    
    Extends the subscription expiration by calling MS365 Graph API
    and updating the database record.
    
    Args:
        subscription_id: UUID of the subscription in our database
        request: New expiration settings
        
    Returns:
        Updated subscription details
        
    Example:
        PATCH /webhooks/ms365/subscriptions/123e4567.../renew
        {"expiration_hours": 72}
    """
    try:
        # Get subscription from database
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT credential_id, external_subscription_id
                    FROM api.webhook_subscriptions
                    WHERE id = %s
                """, (subscription_id,))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Subscription not found")
                
                credential_id = str(row[0])
                external_sub_id = row[1]
            
            # Renew via MS365 Graph API
            result = await renew_subscription(
                credential_id=credential_id,
                subscription_id=external_sub_id,
                expiration_hours=request.expiration_hours
            )
            
            # Update database
            with conn.cursor() as cur:
                expires_at = datetime.fromisoformat(result["expires_at"].replace('Z', '+00:00'))
                
                cur.execute("""
                    UPDATE api.webhook_subscriptions
                    SET expires_at = %s, updated_at = NOW(), status = 'active'
                    WHERE id = %s
                    RETURNING id, credential_id, provider, external_subscription_id,
                              resource_path, notification_url, change_types, status,
                              expires_at, created_at, last_notification_at
                """, (expires_at, subscription_id))
                
                row = cur.fetchone()
                conn.commit()
                
                return SubscriptionResponse(
                    id=str(row[0]),
                    credential_id=str(row[1]),
                    provider=row[2],
                    external_subscription_id=row[3],
                    resource_path=row[4],
                    notification_url=row[5],
                    change_types=row[6],
                    status=row[7],
                    expires_at=row[8],
                    created_at=row[9],
                    last_notification_at=row[10]
                )
        finally:
            conn.close()
            
    except MS365ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to renew subscription: {str(e)}")


@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def delete_webhook_subscription(subscription_id: str):
    """
    Delete a webhook subscription.
    
    This will:
    1. Delete the subscription from MS365 Graph API
    2. Mark the subscription as deleted in database (or remove it)
    
    Args:
        subscription_id: UUID of the subscription in our database
        
    Returns:
        204 No Content on success
        
    Example:
        DELETE /webhooks/ms365/subscriptions/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        # Get subscription from database
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT credential_id, external_subscription_id
                    FROM api.webhook_subscriptions
                    WHERE id = %s
                """, (subscription_id,))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Subscription not found")
                
                credential_id = str(row[0])
                external_sub_id = row[1]
            
            # Delete from MS365 Graph API
            await delete_subscription(
                credential_id=credential_id,
                subscription_id=external_sub_id
            )
            
            # Remove from database (or mark as deleted)
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM api.webhook_subscriptions
                    WHERE id = %s
                """, (subscription_id,))
                
                conn.commit()
        finally:
            conn.close()
            
    except MS365ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete subscription: {str(e)}")


# ============================================================================
# Webhook Receiver Endpoint
# ============================================================================

@router.post("/webhook", status_code=202)
async def receive_ms365_webhook(
    request: Request,
    validationToken: Optional[str] = Query(None)
):
    """
    Receive MS365 webhook notifications.
    
    This endpoint handles two scenarios:
    
    1. **Validation Challenge** (during subscription creation):
       MS365 sends a GET with ?validationToken=xxx
       We must return the token as plain text with 200 OK
       
    2. **Change Notifications** (after subscription is active):
       MS365 POSTs an array of notifications
       We store them in webhook_events table with idempotency
       We return 202 Accepted immediately
    
    Idempotency:
        Uses (credential_id, subscriptionId, resourceData.id) as unique key
        Prevents duplicate processing of the same event
    
    MS365 Requirements:
        - Must respond within 3 seconds
        - Must return 202 for notifications (not 200)
        - Must return 200 with validationToken for validation
        - Endpoint must be HTTPS
        - Endpoint must be publicly accessible
    
    Example Validation Request:
        POST /webhooks/ms365/webhook?validationToken=abc123
        
    Example Notification Request:
        POST /webhooks/ms365/webhook
        {
          "value": [
            {
              "subscriptionId": "7f366c7e-...",
              "clientState": "secret123",
              "changeType": "created",
              "resource": "Users/{userId}/Messages/{messageId}",
              "resourceData": {
                "@odata.type": "#Microsoft.Graph.Message",
                "@odata.id": "Users/{userId}/Messages/{messageId}",
                "id": "{messageId}"
              },
              "subscriptionExpirationDateTime": "2025-11-17T18:00:00Z",
              "tenantId": "{tenantId}"
            }
          ]
        }
    """
    
    # Handle validation challenge (subscription creation)
    if validationToken:
        print(f"Received validation challenge: {validationToken}")
        return PlainTextResponse(content=validationToken, status_code=200)
    
    # Handle change notifications
    try:
        body = await request.json()
        notifications = body.get("value", [])
        
        if not notifications:
            print("Received empty notification")
            return {"status": "accepted", "message": "No notifications to process"}
        
        print(f"Received {len(notifications)} notification(s)")
        
        # Process each notification
        conn = get_db_connection()
        try:
            stored_count = 0
            duplicate_count = 0
            
            for notification in notifications:
                subscription_id = notification.get("subscriptionId")
                change_type = notification.get("changeType")
                resource = notification.get("resource")
                resource_data = notification.get("resourceData", {})
                external_resource_id = resource_data.get("id") or resource_data.get("@odata.id")
                
                if not subscription_id or not external_resource_id:
                    print(f"Invalid notification: missing subscriptionId or resourceId")
                    continue
                
                # Look up subscription to get credential_id
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, credential_id
                        FROM api.webhook_subscriptions
                        WHERE external_subscription_id = %s
                    """, (subscription_id,))
                    
                    row = cur.fetchone()
                    if not row:
                        print(f"Subscription {subscription_id} not found in database")
                        continue
                    
                    internal_sub_id = str(row[0])
                    credential_id = str(row[1])
                
                # Generate idempotency key
                idempotency_key = f"{credential_id}:{subscription_id}:{external_resource_id}"
                
                # Store event with idempotency check
                with conn.cursor() as cur:
                    try:
                        cur.execute("""
                            INSERT INTO api.webhook_events (
                                credential_id,
                                subscription_id,
                                provider,
                                event_type,
                                idempotency_key,
                                external_resource_id,
                                raw_payload,
                                status
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            credential_id,
                            internal_sub_id,
                            'ms365',
                            change_type,
                            idempotency_key,
                            external_resource_id,
                            json.dumps(notification),
                            'pending'
                        ))
                        
                        event_id = cur.fetchone()[0]
                        stored_count += 1
                        print(f"Stored event {event_id} for resource {external_resource_id}")
                        
                    except Exception as e:
                        # Likely duplicate (idempotency_key constraint)
                        if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                            duplicate_count += 1
                            print(f"Duplicate event for resource {external_resource_id} (idempotency)")
                        else:
                            print(f"Error storing event: {e}")
                            raise
                
                # Update subscription last_notification_at
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE api.webhook_subscriptions
                        SET last_notification_at = NOW(), updated_at = NOW()
                        WHERE external_subscription_id = %s
                    """, (subscription_id,))
            
            conn.commit()
            
            print(f"Webhook processing complete: {stored_count} stored, {duplicate_count} duplicates")
            
            return {
                "status": "accepted",
                "stored": stored_count,
                "duplicates": duplicate_count,
                "total": len(notifications)
            }
            
        finally:
            conn.close()
    
    except json.JSONDecodeError:
        print("Invalid JSON in webhook request")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Return 202 anyway to acknowledge receipt (MS365 requirement)
        # The error will be logged but won't block MS365 from considering it received
        return {"status": "accepted", "error": str(e)}
