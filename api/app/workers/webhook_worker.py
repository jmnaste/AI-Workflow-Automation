"""
Webhook Event Processing Worker

Background task that processes pending webhook events.
Fetches full resource data from MS365 and normalizes for business logic consumption.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import traceback

from ..services.ms365_service import fetch_message, MS365ServiceError
from ..services.database import get_db_connection


# Configuration
WORKER_INTERVAL_SECONDS = int(os.getenv("WEBHOOK_WORKER_INTERVAL", "10"))
WORKER_BATCH_SIZE = int(os.getenv("WEBHOOK_WORKER_BATCH_SIZE", "10"))
MAX_RETRY_ATTEMPTS = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))


async def process_pending_events(batch_size: int = WORKER_BATCH_SIZE) -> Dict[str, int]:
    """
    Process pending webhook events from the database.
    
    Workflow:
    1. Query webhook_events WHERE status='pending' LIMIT batch_size
    2. For each event:
       - Extract message_id from raw_payload
       - Fetch full message data via MS365 Graph API
       - Normalize to standard format
       - Store in normalized_payload column
       - Update status to 'completed'
    3. Handle failures with retry logic
    
    Args:
        batch_size: Maximum number of events to process in one run
        
    Returns:
        Stats dict with counts: processed, failed, skipped
    """
    stats = {
        "processed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    conn = get_db_connection()
    try:
        # Fetch pending events
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, credential_id, subscription_id, provider, event_type,
                       external_resource_id, raw_payload, retry_count
                FROM api.webhook_events
                WHERE status = 'pending' AND retry_count < %s
                ORDER BY received_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            """, (MAX_RETRY_ATTEMPTS, batch_size))
            
            events = cur.fetchall()
        
        if not events:
            return stats
        
        print(f"Processing {len(events)} pending webhook events")
        
        for event in events:
            event_id = str(event[0])
            credential_id = str(event[1])
            subscription_id = str(event[2])
            provider = event[3]
            event_type = event[4]
            external_resource_id = event[5]
            raw_payload = event[6]
            retry_count = event[7]
            
            try:
                # Mark as processing
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE api.webhook_events
                        SET status = 'processing'
                        WHERE id = %s
                    """, (event_id,))
                    conn.commit()
                
                # Process based on provider
                if provider == 'ms365':
                    normalized = await process_ms365_event(
                        credential_id=credential_id,
                        event_type=event_type,
                        external_resource_id=external_resource_id,
                        raw_payload=raw_payload
                    )
                else:
                    print(f"Unsupported provider: {provider}")
                    stats["skipped"] += 1
                    continue
                
                # Store normalized payload and mark completed
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE api.webhook_events
                        SET 
                            normalized_payload = %s,
                            status = 'completed',
                            processed_at = NOW()
                        WHERE id = %s
                    """, (json.dumps(normalized), event_id))
                    conn.commit()
                
                stats["processed"] += 1
                print(f"✓ Processed event {event_id} ({event_type})")
                
            except Exception as e:
                # Handle failure with retry logic
                error_message = str(e)
                traceback_str = traceback.format_exc()
                
                print(f"✗ Failed to process event {event_id}: {error_message}")
                
                # Increment retry count
                new_retry_count = retry_count + 1
                
                # Determine final status
                if new_retry_count >= MAX_RETRY_ATTEMPTS:
                    final_status = 'failed'
                    print(f"  Max retries reached ({MAX_RETRY_ATTEMPTS}), marking as failed")
                else:
                    final_status = 'pending'
                    print(f"  Will retry (attempt {new_retry_count}/{MAX_RETRY_ATTEMPTS})")
                
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE api.webhook_events
                        SET 
                            status = %s,
                            retry_count = %s,
                            error_message = %s
                        WHERE id = %s
                    """, (final_status, new_retry_count, error_message[:500], event_id))
                    conn.commit()
                
                stats["failed"] += 1
        
        return stats
        
    finally:
        conn.close()


async def process_ms365_event(
    credential_id: str,
    event_type: str,
    external_resource_id: str,
    raw_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process MS365 webhook event.
    
    Fetches full message data from Graph API and normalizes to standard format.
    
    Args:
        credential_id: UUID of the credential
        event_type: Type of change (created, updated, deleted)
        external_resource_id: MS365 message ID
        raw_payload: Original webhook notification
        
    Returns:
        Normalized event data
        
    Raises:
        MS365ServiceError: If fetching message fails
    """
    # Extract message ID from resource path or resourceData
    message_id = external_resource_id
    
    # For 'deleted' events, we can't fetch the message (it's gone)
    if event_type == 'deleted':
        return {
            "event_type": event_type,
            "message_id": message_id,
            "deleted": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Fetch full message data via Graph API
    try:
        message_data = await fetch_message(credential_id, message_id)
        
        # Normalize to standard format
        normalized = {
            "event_type": event_type,
            "provider": "ms365",
            "message": {
                "id": message_data["id"],
                "subject": message_data["subject"],
                "from": message_data["from"],
                "received_at": message_data["received_at"],
                "body_preview": message_data["body_preview"],
                "body_content": message_data.get("body_content"),
                "body_type": message_data.get("body_type", "text"),
                "has_attachments": message_data["has_attachments"],
                "is_read": message_data.get("is_read", False),
                "importance": message_data.get("importance", "normal")
            },
            "raw_notification": raw_payload,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        return normalized
        
    except MS365ServiceError as e:
        raise Exception(f"Failed to fetch MS365 message {message_id}: {e}")


async def run_worker_loop():
    """
    Main worker loop - runs continuously processing events.
    
    This should be started as a background task in the FastAPI lifespan.
    """
    print(f"Webhook worker started (interval: {WORKER_INTERVAL_SECONDS}s, batch: {WORKER_BATCH_SIZE})")
    
    while True:
        try:
            stats = await process_pending_events()
            
            if stats["processed"] > 0 or stats["failed"] > 0:
                print(f"Worker cycle: processed={stats['processed']}, failed={stats['failed']}, skipped={stats['skipped']}")
            
        except Exception as e:
            print(f"Worker error: {e}")
            traceback.print_exc()
        
        # Wait before next cycle
        await asyncio.sleep(WORKER_INTERVAL_SECONDS)


# Manual trigger function for testing/debugging
async def process_single_event(event_id: str) -> bool:
    """
    Process a specific event by ID (for testing/debugging).
    
    Args:
        event_id: UUID of the event to process
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT credential_id, subscription_id, provider, event_type,
                       external_resource_id, raw_payload, retry_count
                FROM api.webhook_events
                WHERE id = %s
            """, (event_id,))
            
            row = cur.fetchone()
            if not row:
                print(f"Event {event_id} not found")
                return False
            
            credential_id = str(row[0])
            provider = row[2]
            event_type = row[3]
            external_resource_id = row[4]
            raw_payload = row[5]
        
        if provider == 'ms365':
            normalized = await process_ms365_event(
                credential_id=credential_id,
                event_type=event_type,
                external_resource_id=external_resource_id,
                raw_payload=raw_payload
            )
            
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE api.webhook_events
                    SET 
                        normalized_payload = %s,
                        status = 'completed',
                        processed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(normalized), event_id))
                conn.commit()
            
            print(f"✓ Processed event {event_id}")
            return True
        else:
            print(f"Unsupported provider: {provider}")
            return False
            
    except Exception as e:
        print(f"Error processing event {event_id}: {e}")
        traceback.print_exc()
        return False
    finally:
        conn.close()
