# Process + Adapters Refactoring Plan

**Date**: 2025-11-15  
**Status**: Planning  
**Goal**: Refactor API service to use Process + Adapters layered architecture

---

## Current State

```
api/app/
├── services/
│   ├── ms365_service.py       # MS365 Graph API integration
│   ├── auth_client.py         # Token vending client
│   ├── database.py            # Database utilities
│   └── migrations.py          # Migration runner
├── routes/
│   └── ms365.py               # Webhook receiver + subscription management
├── workers/
│   └── webhook_worker.py      # Background event processor
└── main.py
```

**Issues**:
- No clear separation between business logic and technical integrations
- `ms365_service.py` is adapter-level but sits in `services/`
- No process layer for business workflows
- n8n will need process-level endpoints (not yet implemented)

---

## Target State

```
api/app/
├── processes/                           # NEW: Business workflows
│   ├── __init__.py
│   ├── email_classification.py         # Classify email intent
│   ├── quote_processing.py             # Handle quote requests
│   ├── workspace_management.py         # Create/manage workspaces
│   └── document_analysis.py            # Extract document data
│
├── adapters/                            # NEW: External integrations
│   ├── __init__.py
│   ├── ms365_adapter.py                # MOVED from services/ms365_service.py
│   ├── googlews_adapter.py             # FUTURE
│   ├── database_adapter.py             # Database queries
│   └── storage_adapter.py              # File/folder management
│
├── routes/
│   ├── ms365.py                        # Webhook receiver (adapter-level)
│   ├── googlews.py                     # FUTURE
│   └── processes.py                    # NEW: Business endpoints for n8n
│
├── workers/
│   └── webhook_worker.py               # UPDATED: Call process layer
│
├── models/                              # NEW: Data models
│   ├── events.py                       # Webhook event schemas
│   └── processes.py                    # Process request/response schemas
│
├── services/                            # Keep internal services
│   ├── auth_client.py                  # Keep (internal service)
│   ├── database.py                     # Keep (utilities)
│   └── migrations.py                   # Keep (migration runner)
│
└── main.py                              # UPDATED: Register processes router
```

---

## Migration Steps

### **Phase 1: Create Adapters Layer (1-2 hours)**

**Goal**: Move existing code to adapters without breaking anything

1. **Create adapters directory**:
   ```bash
   mkdir api/app/adapters
   touch api/app/adapters/__init__.py
   ```

2. **Move MS365 service to adapter**:
   ```bash
   mv api/app/services/ms365_service.py api/app/adapters/ms365_adapter.py
   ```

3. **Update imports**:
   - In `api/app/routes/ms365.py`: Change `from ..services.ms365_service` → `from ..adapters.ms365_adapter`
   - In `api/app/workers/webhook_worker.py`: Same import update
   - In test files: Update imports

4. **Create database adapter** (`api/app/adapters/database_adapter.py`):
   ```python
   """Database adapter for PostgreSQL operations"""
   from ..services.database import get_db_connection
   
   async def get_webhook_event(event_id: str) -> dict:
       """Fetch webhook event by ID"""
       conn = get_db_connection()
       try:
           with conn.cursor() as cur:
               cur.execute("""
                   SELECT id, credential_id, provider, event_type,
                          external_resource_id, raw_payload, normalized_payload
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
                   "normalized_payload": row[6]
               }
       finally:
           conn.close()
   
   async def list_pending_events(limit: int = 10) -> list[dict]:
       """List pending webhook events for n8n polling"""
       # Implementation
       pass
   ```

5. **Create storage adapter skeleton** (`api/app/adapters/storage_adapter.py`):
   ```python
   """Storage adapter for file/folder operations"""
   import os
   import json
   from pathlib import Path
   
   WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/workspace")
   
   async def create_workspace_folder(folder_name: str) -> str:
       """Create workspace folder, return absolute path"""
       folder_path = Path(WORKSPACE_ROOT) / folder_name
       folder_path.mkdir(parents=True, exist_ok=True)
       return str(folder_path)
   
   async def write_json(file_path: str, data: dict):
       """Write JSON data to file"""
       with open(file_path, 'w') as f:
           json.dump(data, f, indent=2)
   
   async def save_attachment(file_path: str, content: bytes):
       """Save attachment content to file"""
       Path(file_path).parent.mkdir(parents=True, exist_ok=True)
       with open(file_path, 'wb') as f:
           f.write(content)
   ```

6. **Update adapters __init__.py**:
   ```python
   """Adapters layer: External system integrations"""
   from . import ms365_adapter
   from . import database_adapter
   from . import storage_adapter
   
   __all__ = ["ms365_adapter", "database_adapter", "storage_adapter"]
   ```

7. **Test**: Run existing tests, verify nothing broke

---

### **Phase 2: Create Process Layer (2-3 hours)**

**Goal**: Implement business workflows that use adapters

1. **Create processes directory**:
   ```bash
   mkdir api/app/processes
   touch api/app/processes/__init__.py
   ```

2. **Implement email classification** (`api/app/processes/email_classification.py`):
   ```python
   """Email classification process: Analyze intent and extract entities"""
   from ..adapters import database_adapter
   
   async def analyze_email(event_id: str) -> dict:
       """
       Classify email intent and extract entities
       
       Returns:
           {
               "intent": "quote_request" | "invoice" | "general",
               "confidence": 0.95,
               "entities": [
                   {"type": "product", "value": "Widget X"},
                   {"type": "quantity", "value": 10}
               ],
               "suggested_actions": ["create_quote", "notify_sales"]
           }
       """
       # Get event from database
       event = await database_adapter.get_webhook_event(event_id)
       if not event:
           raise ValueError(f"Event {event_id} not found")
       
       message = event['normalized_payload']['message']
       
       # Simple rule-based classification for MVP
       subject_lower = message['subject'].lower()
       body_lower = message.get('body_preview', '').lower()
       
       # Detect quote request
       if 'quote' in subject_lower or 'quotation' in subject_lower or 'price' in body_lower:
           return {
               "intent": "quote_request",
               "confidence": 0.90,
               "entities": extract_quote_entities(message),
               "suggested_actions": ["create_quote", "notify_sales"]
           }
       
       # Detect invoice
       if 'invoice' in subject_lower or 'bill' in subject_lower:
           return {
               "intent": "invoice",
               "confidence": 0.85,
               "entities": extract_invoice_entities(message),
               "suggested_actions": ["process_invoice", "notify_accounting"]
           }
       
       # General email
       return {
           "intent": "general",
           "confidence": 0.50,
           "entities": [],
           "suggested_actions": ["archive"]
       }
   
   def extract_quote_entities(message: dict) -> list[dict]:
       """Extract product names, quantities from message"""
       # TODO: Implement with regex or AI
       return []
   
   def extract_invoice_entities(message: dict) -> list[dict]:
       """Extract invoice number, amount, due date"""
       # TODO: Implement
       return []
   ```

3. **Implement quote processing** (`api/app/processes/quote_processing.py`):
   ```python
   """Quote processing workflow"""
   from ..adapters import ms365_adapter, database_adapter, storage_adapter
   from datetime import datetime
   
   async def handle_quote_request(
       event_id: str,
       folder_name: str = None,
       extract_attachments: bool = True
   ) -> dict:
       """
       Process quote request email: create workspace with message + attachments
       
       Returns:
           {
               "folder_path": "/workspace/Quote_JohnDoe_2025-11-15",
               "files_created": ["message.json", "metadata.json", "attachments/image1.jpg"]
           }
       """
       # Get event
       event = await database_adapter.get_webhook_event(event_id)
       message = event['normalized_payload']['message']
       credential_id = event['credential_id']
       
       # Generate folder name if not provided
       if not folder_name:
           from_name = message['from'].get('name', 'Unknown').replace(' ', '_')
           date_str = datetime.now().strftime('%Y-%m-%d')
           folder_name = f"Quote_{from_name}_{date_str}"
       
       # Create workspace folder
       folder_path = await storage_adapter.create_workspace_folder(folder_name)
       
       # Write message.json
       await storage_adapter.write_json(f"{folder_path}/message.json", message)
       
       # Analyze and write metadata.json
       from . import email_classification
       analysis = await email_classification.analyze_email(event_id)
       await storage_adapter.write_json(f"{folder_path}/metadata.json", analysis)
       
       files_created = ["message.json", "metadata.json"]
       
       # Download and save attachments
       if extract_attachments and message['has_attachments']:
           attachments = await ms365_adapter.download_attachments(
               credential_id,
               message['id']
           )
           
           for attachment in attachments:
               file_path = f"{folder_path}/attachments/{attachment['name']}"
               await storage_adapter.save_attachment(file_path, attachment['content'])
               files_created.append(f"attachments/{attachment['name']}")
       
       return {
           "folder_path": folder_path,
           "files_created": files_created
       }
   ```

4. **Implement workspace management** (`api/app/processes/workspace_management.py`):
   ```python
   """Workspace management process: Generic folder creation"""
   from ..adapters import database_adapter, storage_adapter, ms365_adapter
   
   async def create_workspace(
       event_id: str,
       folder_name: str,
       options: dict = None
   ) -> dict:
       """
       Generic workspace creation: flexible options for different use cases
       
       Options:
           - include_message: bool (default True)
           - include_metadata: bool (default True)
           - extract_attachments: bool (default True)
           - custom_files: list of {name, content} dicts
       """
       options = options or {}
       
       # Get event
       event = await database_adapter.get_webhook_event(event_id)
       message = event['normalized_payload']['message']
       
       # Create folder
       folder_path = await storage_adapter.create_workspace_folder(folder_name)
       files_created = []
       
       # Write files based on options
       if options.get('include_message', True):
           await storage_adapter.write_json(f"{folder_path}/message.json", message)
           files_created.append("message.json")
       
       if options.get('include_metadata', True):
           from . import email_classification
           analysis = await email_classification.analyze_email(event_id)
           await storage_adapter.write_json(f"{folder_path}/metadata.json", analysis)
           files_created.append("metadata.json")
       
       if options.get('extract_attachments', True) and message['has_attachments']:
           attachments = await ms365_adapter.download_attachments(
               event['credential_id'],
               message['id']
           )
           for att in attachments:
               file_path = f"{folder_path}/attachments/{att['name']}"
               await storage_adapter.save_attachment(file_path, att['content'])
               files_created.append(f"attachments/{att['name']}")
       
       return {"folder_path": folder_path, "files_created": files_created}
   ```

5. **Update processes __init__.py**:
   ```python
   """Processes layer: Business workflows"""
   from . import email_classification
   from . import quote_processing
   from . import workspace_management
   
   __all__ = [
       "email_classification",
       "quote_processing",
       "workspace_management"
   ]
   ```

---

### **Phase 3: Add Process Endpoints (1 hour)**

**Goal**: Expose process-level APIs for n8n

1. **Create processes router** (`api/app/routes/processes.py`):
   ```python
   """Process-level API endpoints for n8n workflows"""
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from typing import Optional, List
   
   from ..processes import email_classification, quote_processing, workspace_management
   
   router = APIRouter(prefix="/processes", tags=["processes"])
   
   
   # Request models
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
       """Process quote request: create workspace with message + attachments"""
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
   
   
   # n8n polling endpoint
   @router.get("/events/pending")
   async def list_pending_events(since: Optional[str] = None, limit: int = 10):
       """List pending events for n8n polling"""
       from ..adapters import database_adapter
       events = await database_adapter.list_pending_events(limit)
       return {"status": "success", "count": len(events), "events": events}
   ```

2. **Register router in main.py**:
   ```python
   from .routes import ms365, processes
   
   app.include_router(ms365.router)
   app.include_router(processes.router)  # NEW
   ```

3. **Add download endpoint** for attachments:
   ```python
   # In processes.py
   from fastapi.responses import FileResponse
   
   @router.get("/attachments/download")
   async def download_attachment(
       event_id: str,
       attachment_name: str
   ):
       """Download attachment from processed event"""
       # Implementation: find file in workspace, return as FileResponse
       pass
   ```

---

### **Phase 4: Update Worker (30 min)**

**Goal**: Worker stays simple, just normalizes data. Process layer handles complex logic.

No changes needed! Worker already normalizes data and stores in `normalized_payload`. Process layer reads from there.

---

### **Phase 5: Add MS365 Attachment Download (1 hour)**

**Goal**: Implement attachment download in MS365 adapter

Update `api/app/adapters/ms365_adapter.py`:
```python
async def download_attachments(credential_id: str, message_id: str) -> list[dict]:
    """
    Download all attachments from MS365 message
    
    Returns:
        [{"name": "file.jpg", "content": bytes, "content_type": "image/jpeg", "size": 12345}]
    """
    graph_client = await get_graph_client(credential_id)
    
    attachments_response = await graph_client.me.messages.by_message_id(message_id)\
        .attachments.get()
    
    results = []
    for attachment in attachments_response.value:
        if hasattr(attachment, 'content_bytes'):
            # File attachment
            results.append({
                "name": attachment.name,
                "content": base64.b64decode(attachment.content_bytes),
                "content_type": attachment.content_type,
                "size": attachment.size
            })
    
    return results
```

---

## Testing Plan

### **Unit Tests**
```python
# tests/test_processes/test_email_classification.py
async def test_classify_quote_request():
    result = await email_classification.analyze_email(mock_event_id)
    assert result["intent"] == "quote_request"
    assert result["confidence"] > 0.8

# tests/test_adapters/test_ms365_adapter.py
async def test_download_attachments():
    attachments = await ms365_adapter.download_attachments(cred_id, msg_id)
    assert len(attachments) > 0
    assert "content" in attachments[0]
```

### **Integration Tests**
```bash
# Test complete workflow
curl -X POST https://console.flovify.ca/bff/api/processes/quote/handle \
  -H "Content-Type: application/json" \
  -d '{"event_id": "EVENT_UUID", "folder_name": "Test_Quote"}'

# Verify folder created
ls /workspace/Test_Quote/
# Expected: message.json, metadata.json, attachments/
```

---

## Rollout Strategy

### **Option A: Big Bang (2-3 days)**
1. Complete all phases in development
2. Test thoroughly
3. Deploy all changes at once

### **Option B: Incremental (1 week)**
1. Deploy Phase 1 (adapters refactor) - backward compatible
2. Deploy Phase 2-3 (add process layer) - new endpoints don't break existing
3. Deploy Phase 4-5 (worker update, attachments) - final features

**Recommendation**: Option B (Incremental) - safer, allows testing in production

---

## Success Criteria

- ✅ All existing tests pass
- ✅ Webhook pipeline still works (receive → process → normalize)
- ✅ New process endpoints accessible
- ✅ n8n can call `/api/processes/quote/handle` successfully
- ✅ Workspace folder created with message.json, metadata.json, attachments/
- ✅ Code structure follows Process + Adapters pattern
- ✅ Documentation updated

---

## Timeline Estimate

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 1: Adapters Layer | 1-2 hours | HIGH |
| Phase 2: Process Layer | 2-3 hours | HIGH |
| Phase 3: Process Endpoints | 1 hour | HIGH |
| Phase 4: Worker Update | 30 min | MEDIUM |
| Phase 5: Attachment Download | 1 hour | HIGH |
| **Total** | **5-7 hours** | |

---

**Ready to start Phase 1?**
