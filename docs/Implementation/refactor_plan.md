# Refactoring Plan: Transition to Process + Adapters Architecture

**Date**: 2025-11-15  
**Status**: Ready to Execute  
**Estimated Time**: 10-14 hours across 5 phases

---

## Overview

This plan transitions the codebase from current structure to the approved **Process + Adapters** architecture.

**Current State**: Monolithic `services/ms365_service.py` with mixed concerns  
**Target State**: Layered architecture with separate process and adapter layers

---

## Prerequisites

✅ Architecture documented (`architecture_decision.md`)  
✅ Terminology agreed upon (Adapter, Service, Primitive, Process)  
⏳ Current code tested (webhook pipeline functional)

---

## Phase 0: Test Current Implementation

**Duration**: 30-60 minutes  
**Status**: In Progress (3/8 complete)

### **Goal**
Verify current webhook pipeline works before refactoring

### **Tasks**
- [x] Test service health
- [x] Test credential connection
- [x] Test MS365 message fetching
- [ ] Test webhook subscription creation
- [ ] Test webhook notification receiving
- [ ] Test worker processing
- [ ] Test subscription management (list, renew, delete)
- [ ] Test error handling (retries)

### **Success Criteria**
- All endpoints respond correctly
- Webhook receives and processes events
- Worker normalizes data successfully
- Database shows completed events

---

## Phase 1: Create Adapter Structure

**Duration**: 2-3 hours  
**Status**: Not Started

### **Goal**
Reorganize existing code into adapter structure without breaking functionality

### **Step 1.1: Create Directory Structure**

```bash
# Create adapter directories
mkdir -p api/app/adapters/ms365
mkdir -p api/app/adapters/googlews
touch api/app/adapters/__init__.py
touch api/app/adapters/ms365/__init__.py
touch api/app/adapters/googlews/__init__.py
```

### **Step 1.2: Refactor MS365 Service to Adapter**

**Current File**: `api/app/services/ms365_service.py` (370 lines)

**Split Into**:

1. **`api/app/adapters/ms365/_auth.py`** - Authentication (internal module)
   ```python
   """MS365 Authentication - Internal Module"""
   # Move: FlovifyTokenCredential class
   # Move: get_graph_client() function
   ```

2. **`api/app/adapters/ms365/mail.py`** - Email primitives
   ```python
   """MS365 Mail Service: Email primitives for Microsoft 365"""
   # Move: fetch_message() → get_message()
   # Move: list_messages()
   # Move: download_attachments()
   # Add: send_message() (new)
   # Add: move_message() (new)
   # Add: mark_as_read() (new)
   ```

3. **`api/app/adapters/ms365/subscriptions.py`** - Webhook subscriptions
   ```python
   """MS365 Subscription Management: Webhook subscription primitives"""
   # Move: create_subscription()
   # Move: renew_subscription()
   # Move: delete_subscription()
   ```

### **Step 1.3: Update MS365 Adapter Exports**

**File**: `api/app/adapters/ms365/__init__.py`
```python
"""Microsoft 365 Adapter: Integration with MS365 Graph API"""

from . import mail
from . import subscriptions

__all__ = ["mail", "subscriptions"]
```

### **Step 1.4: Update Imports Across Codebase**

**Files to Update**:
1. `api/app/routes/ms365.py`
   ```python
   # Old:
   from ..services import ms365_service
   
   # New:
   from ..adapters.ms365 import mail, subscriptions
   ```

2. `api/app/workers/webhook_worker.py`
   ```python
   # Old:
   from ..services.ms365_service import fetch_message
   
   # New:
   from ..adapters.ms365 import mail
   # Use: await mail.get_message(credential_id, message_id)
   ```

3. `api/app/main.py` (test endpoints)
   ```python
   # Old:
   from .services import ms365_service
   
   # New:
   from .adapters.ms365 import mail
   ```

### **Step 1.5: Create Database Adapter**

**File**: `api/app/adapters/database.py`

```python
"""Database Adapter: PostgreSQL query primitives"""

from ..services.database import get_db_connection

async def get_webhook_event(event_id: str) -> dict | None:
    """Fetch webhook event by ID"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, credential_id, provider, event_type,
                       external_resource_id, raw_payload, normalized_payload,
                       status, retry_count, received_at, processed_at
                FROM api.webhook_events
                WHERE id = %s
            """, (event_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                "id": str(row[0]),
                "credential_id": str(row[1]),
                "provider": row[2],
                "event_type": row[3],
                "external_resource_id": row[4],
                "raw_payload": row[5],
                "normalized_payload": row[6],
                "status": row[7],
                "retry_count": row[8],
                "received_at": row[9].isoformat() if row[9] else None,
                "processed_at": row[10].isoformat() if row[10] else None
            }
    finally:
        conn.close()


async def list_pending_events(limit: int = 10, since: str = None) -> list[dict]:
    """List pending/completed events for n8n polling"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if since:
                cur.execute("""
                    SELECT id, credential_id, provider, event_type,
                           external_resource_id, normalized_payload,
                           status, received_at
                    FROM api.webhook_events
                    WHERE received_at > %s
                    ORDER BY received_at DESC
                    LIMIT %s
                """, (since, limit))
            else:
                cur.execute("""
                    SELECT id, credential_id, provider, event_type,
                           external_resource_id, normalized_payload,
                           status, received_at
                    FROM api.webhook_events
                    WHERE status IN ('pending', 'completed')
                    ORDER BY received_at DESC
                    LIMIT %s
                """, (limit,))
            
            rows = cur.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "credential_id": str(row[1]),
                    "provider": row[2],
                    "event_type": row[3],
                    "external_resource_id": row[4],
                    "normalized_payload": row[5],
                    "status": row[6],
                    "received_at": row[7].isoformat() if row[7] else None
                }
                for row in rows
            ]
    finally:
        conn.close()


async def update_event_status(
    event_id: str, 
    status: str, 
    normalized_payload: dict = None,
    error_message: str = None
) -> bool:
    """Update webhook event status and optional payload"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if normalized_payload:
                cur.execute("""
                    UPDATE api.webhook_events
                    SET status = %s, normalized_payload = %s, processed_at = NOW()
                    WHERE id = %s
                """, (status, json.dumps(normalized_payload), event_id))
            elif error_message:
                cur.execute("""
                    UPDATE api.webhook_events
                    SET status = %s, error_message = %s, retry_count = retry_count + 1
                    WHERE id = %s
                """, (status, error_message, event_id))
            else:
                cur.execute("""
                    UPDATE api.webhook_events
                    SET status = %s
                    WHERE id = %s
                """, (status, event_id))
            conn.commit()
            return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
```

### **Step 1.6: Create Storage Adapter**

**File**: `api/app/adapters/storage.py`

```python
"""Storage Adapter: File system operations for workspace management"""

import os
import json
from pathlib import Path
from typing import Any

# Configurable workspace root (env var or default)
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/workspace")


async def create_workspace_folder(folder_name: str) -> str:
    """
    Create workspace folder with subdirectories
    
    Returns: Absolute path to created folder
    """
    folder_path = Path(WORKSPACE_ROOT) / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Create standard subdirectories
    (folder_path / "attachments").mkdir(exist_ok=True)
    
    return str(folder_path)


async def write_json(file_path: str, data: dict) -> None:
    """Write JSON data to file"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def save_attachment(file_path: str, content: bytes) -> None:
    """Save attachment content to file"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'wb') as f:
        f.write(content)


async def read_json(file_path: str) -> dict:
    """Read JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def list_files(folder_path: str) -> list[str]:
    """List all files in folder (recursive)"""
    path = Path(folder_path)
    if not path.exists():
        return []
    
    return [str(p.relative_to(path)) for p in path.rglob('*') if p.is_file()]


async def folder_exists(folder_path: str) -> bool:
    """Check if folder exists"""
    return Path(folder_path).exists()
```

### **Step 1.7: Update Adapters Package Exports**

**File**: `api/app/adapters/__init__.py`
```python
"""Adapters Layer: External system integrations"""

from . import ms365
from . import database
from . import storage

__all__ = ["ms365", "database", "storage"]
```

### **Step 1.8: Test After Refactoring**

```bash
# Run existing tests
pytest tests/

# Test endpoints still work
curl http://api:8000/api/health
curl http://api:8000/api/test/ms365/messages/{CREDENTIAL_ID}?limit=3
```

### **Success Criteria**
- ✅ All existing tests pass
- ✅ Webhook pipeline still functional
- ✅ No import errors
- ✅ Code organized into adapters structure

---

## Phase 2: Create Process Layer

**Duration**: 3-4 hours  
**Status**: Not Started

### **Goal**
Implement business workflows that use adapters

### **Step 2.1: Create Process Directory**

```bash
mkdir -p api/app/processes
touch api/app/processes/__init__.py
```

### **Step 2.2: Implement Email Classification Process**

**File**: `api/app/processes/email_classification.py`

See full implementation in `platform_agnostic_processes.md` document.

Key functions:
- `async def analyze_email(event_id: str) -> dict`
- `def extract_quote_entities(message: dict) -> list`
- `def extract_invoice_entities(message: dict) -> list`

### **Step 2.3: Implement Quote Processing Workflow**

**File**: `api/app/processes/quote_processing.py`

Key functions:
- `async def handle_quote_request(event_id, folder_name, extract_attachments) -> dict`

### **Step 2.4: Implement Workspace Management**

**File**: `api/app/processes/workspace_management.py`

Key functions:
- `async def create_workspace(event_id, folder_name, options) -> dict`

### **Step 2.5: Update Processes Package Exports**

**File**: `api/app/processes/__init__.py`
```python
"""Processes Layer: Business workflows"""

from . import email_classification
from . import quote_processing
from . import workspace_management

__all__ = [
    "email_classification",
    "quote_processing",
    "workspace_management"
]
```

### **Success Criteria**
- ✅ Process functions implement business logic
- ✅ Processes use adapters (no direct external dependencies)
- ✅ Unit tests pass with mocked adapters

---

## Phase 3: Add Process-Level API Endpoints

**Duration**: 1-2 hours  
**Status**: Not Started

### **Goal**
Expose process workflows via REST API for n8n

### **Step 3.1: Create Process Routes**

**File**: `api/app/routes/processes.py`

```python
"""Process-level API endpoints for n8n workflows"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..processes import email_classification, quote_processing, workspace_management

router = APIRouter(prefix="/processes", tags=["processes"])


# Request/Response Models
class AnalyzeEmailRequest(BaseModel):
    event_id: str


class HandleQuoteRequest(BaseModel):
    event_id: str
    folder_name: Optional[str] = None
    extract_attachments: bool = True


class CreateWorkspaceRequest(BaseModel):
    event_id: str
    folder_name: str
    options: Optional[dict] = None


# Endpoints
@router.post("/email/analyze")
async def analyze_email(request: AnalyzeEmailRequest):
    """Classify email intent and extract entities"""
    try:
        result = await email_classification.analyze_email(request.event_id)
        return {"status": "success", "analysis": result}
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/quote/handle")
async def handle_quote(request: HandleQuoteRequest):
    """Process quote request: create workspace with attachments"""
    try:
        result = await quote_processing.handle_quote_request(
            request.event_id,
            request.folder_name,
            request.extract_attachments
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(500, f"Quote processing failed: {str(e)}")


@router.post("/workspace/create")
async def create_workspace(request: CreateWorkspaceRequest):
    """Create workspace folder with custom options"""
    try:
        result = await workspace_management.create_workspace(
            request.event_id,
            request.folder_name,
            request.options
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(500, f"Workspace creation failed: {str(e)}")


@router.get("/events/pending")
async def list_pending_events(since: Optional[str] = None, limit: int = 10):
    """List pending events for n8n polling"""
    from ..adapters import database
    events = await database.list_pending_events(limit, since)
    return {"status": "success", "count": len(events), "events": events}
```

### **Step 3.2: Register Process Router**

**File**: `api/app/main.py`
```python
from .routes import ms365, processes

app.include_router(ms365.router)
app.include_router(processes.router)  # NEW
```

### **Step 3.3: Test Process Endpoints**

```bash
# Test email analysis
curl -X POST http://api:8000/api/processes/email/analyze \
  -H "Content-Type: application/json" \
  -d '{"event_id": "EVENT_UUID"}'

# Test quote handling
curl -X POST http://api:8000/api/processes/quote/handle \
  -H "Content-Type: application/json" \
  -d '{"event_id": "EVENT_UUID", "folder_name": "Quote_Test"}'

# Test events polling
curl http://api:8000/api/processes/events/pending?limit=5
```

### **Success Criteria**
- ✅ Process endpoints respond correctly
- ✅ Workflows execute end-to-end
- ✅ Workspace folders created with files
- ✅ n8n can consume endpoints

---

## Phase 4: Add MS365 Primitives

**Duration**: 2-3 hours  
**Status**: Not Started

### **Goal**
Expand MS365 adapter with additional primitives

### **Step 4.1: Add Mail Primitives**

**File**: `api/app/adapters/ms365/mail.py`

Add:
- `async def send_message(credential_id, to, subject, body) -> str`
- `async def move_message(credential_id, message_id, folder_id) -> bool`
- `async def mark_as_read(credential_id, message_id) -> bool`

### **Step 4.2: Create Drive Adapter**

**File**: `api/app/adapters/ms365/drive.py`

Implement:
- `async def create_folder(credential_id, parent_id, name) -> str`
- `async def upload_file(credential_id, folder_id, name, content) -> str`
- `async def move_file(credential_id, file_id, destination_id) -> bool`
- `async def list_files(credential_id, folder_id) -> list`
- `async def download_file(credential_id, file_id) -> bytes`

### **Step 4.3: Update MS365 Adapter Exports**

**File**: `api/app/adapters/ms365/__init__.py`
```python
from . import mail
from . import drive  # NEW
from . import subscriptions

__all__ = ["mail", "drive", "subscriptions"]
```

### **Success Criteria**
- ✅ All MS365 primitives implemented
- ✅ Drive operations work (create folder, upload file)
- ✅ Mail operations expanded (send, move, mark read)

---

## Phase 5: Implement Google Workspace

**Duration**: 4-5 hours  
**Status**: Not Started

### **Goal**
Add Google Workspace adapter matching MS365 interface

### **Step 5.1: Create GoogleWS Auth**

**File**: `api/app/adapters/googlews/_auth.py`

Implement Google OAuth token vending (similar to MS365 FlovifyTokenCredential)

### **Step 5.2: Implement Gmail Primitives**

**File**: `api/app/adapters/googlews/mail.py`

Match MS365 mail primitives:
- `async def get_message(credential_id, message_id) -> dict`
- `async def list_messages(credential_id, folder, limit, filter) -> list`
- `async def send_message(credential_id, to, subject, body) -> str`
- `async def move_message(credential_id, message_id, folder_id) -> bool`
- `async def download_attachments(credential_id, message_id) -> list`

### **Step 5.3: Implement Google Drive Primitives**

**File**: `api/app/adapters/googlews/drive.py`

Match MS365 drive primitives (same signatures!)

### **Step 5.4: Update GoogleWS Adapter Exports**

**File**: `api/app/adapters/googlews/__init__.py`
```python
from . import mail
from . import drive

__all__ = ["mail", "drive"]
```

### **Step 5.5: Test Platform Agnosticism**

```python
# Process works with both providers!
from adapters.ms365 import mail as ms365_mail
from adapters.googlews import mail as google_mail

# Same interface
ms365_message = await ms365_mail.get_message(cred_id, msg_id)
google_message = await google_mail.get_message(cred_id, msg_id)

# Both return normalized format
assert "subject" in ms365_message
assert "subject" in google_message
```

### **Success Criteria**
- ✅ Google Workspace adapter complete
- ✅ Same interface as MS365 adapter
- ✅ Process layer works with both providers
- ✅ Quote workflow works with Gmail

---

## Testing Strategy

### **Unit Tests**
```python
# tests/test_processes/test_email_classification.py
@pytest.mark.asyncio
async def test_classify_quote_request():
    result = await email_classification.analyze_email(mock_event_id)
    assert result["intent"] == "quote_request"
    assert result["confidence"] > 0.8

# tests/test_adapters/test_ms365_mail.py
@pytest.mark.asyncio
async def test_get_message():
    message = await ms365.mail.get_message(cred_id, msg_id)
    assert "subject" in message
    assert "from" in message
```

### **Integration Tests**
```bash
# Test full workflow
curl -X POST http://api:8000/api/processes/quote/handle \
  -d '{"event_id": "abc-123", "folder_name": "Test_Quote"}'

# Verify folder created
ls /workspace/Test_Quote/
# Expected: message.json, metadata.json, attachments/
```

---

## Rollout Options

### **Option A: Big Bang (3-4 days)**
Complete all phases, test thoroughly, deploy all at once

**Pros**: Clean cutover  
**Cons**: Higher risk, longer downtime

### **Option B: Incremental (1 week)** ⭐ RECOMMENDED
1. Deploy Phase 1 (adapters refactor) - backward compatible
2. Deploy Phase 2-3 (process layer + endpoints) - additive
3. Deploy Phase 4-5 (new primitives, GoogleWS) - new features

**Pros**: Lower risk, test in production incrementally  
**Cons**: Requires careful coordination

---

## Timeline Summary

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| 0 | Test current code | 30-60 min | None |
| 1 | Create adapter structure | 2-3 hours | Phase 0 |
| 2 | Create process layer | 3-4 hours | Phase 1 |
| 3 | Add process endpoints | 1-2 hours | Phase 2 |
| 4 | Add MS365 primitives | 2-3 hours | Phase 1 |
| 5 | Implement GoogleWS | 4-5 hours | Phase 4 |
| **Total** | | **13-18 hours** | |

---

## Success Criteria

### **Architecture**
- ✅ Code follows Process + Adapters pattern
- ✅ Clear separation: business vs technical
- ✅ Provider-agnostic process layer

### **Functionality**
- ✅ All existing features work
- ✅ Webhook pipeline functional
- ✅ n8n can call process endpoints
- ✅ Quote workflow creates workspace folders

### **Testing**
- ✅ All tests pass
- ✅ Integration tests validate workflows
- ✅ Manual testing confirms functionality

### **Documentation**
- ✅ Architecture documented
- ✅ Refactor plan complete
- ✅ Platform agnostic patterns documented

---

**Ready to begin? Start with Phase 0 testing completion, then proceed to Phase 1.**
