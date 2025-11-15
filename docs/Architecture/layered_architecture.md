# Layered Architecture: Process + Adapters

**Date**: 2025-11-15  
**Status**: Approved  
**Architecture Pattern**: Hexagonal Architecture (Ports & Adapters)

---

## Overview

Flovify API uses a **two-layer architecture** to separate business logic from technical integrations:

```
┌─────────────────────────────────────────────────────────────┐
│  PROCESS LAYER (Business Workflows)                         │
│  - Email classification                                      │
│  - Quote request processing                                  │
│  - Workspace management                                      │
│  - Document analysis                                         │
└─────────────┬───────────────────────────────────────────────┘
              │
              │ Uses
              ▼
┌─────────────────────────────────────────────────────────────┐
│  ADAPTERS LAYER (External System Integrations)              │
│  - MS365 adapter (Graph API)                                 │
│  - Google Workspace adapter (Gmail API)                      │
│  - Database adapter (PostgreSQL)                             │
│  - Storage adapter (filesystem, S3, etc.)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### **Process Layer (Business)**
- **Purpose**: Orchestrate business workflows and apply business rules
- **Responsibilities**:
  - Coordinate multi-step workflows
  - Apply domain logic (classification, validation, routing)
  - Compose multiple adapters to achieve business goals
  - Provide high-level APIs for n8n consumption
- **Dependencies**: Can depend on Adapters, NOT on external libraries
- **Example**: `quote_processing.py` orchestrates email analysis, attachment extraction, and workspace creation

### **Adapters Layer (Technical)**
- **Purpose**: Abstract external system integrations
- **Responsibilities**:
  - Wrap third-party APIs (MS365, Google, etc.)
  - Handle authentication, retries, rate limiting
  - Normalize data formats from external systems
  - Provide clean, consistent interfaces to Process layer
- **Dependencies**: Can depend on external libraries (msgraph-sdk, google-api, etc.)
- **Example**: `ms365_adapter.py` wraps Microsoft Graph API calls

---

## Folder Structure

```
api/app/
├── processes/                     # PROCESS LAYER
│   ├── __init__.py
│   ├── email_classification.py    # Classify email intent (quote, invoice, etc.)
│   ├── quote_processing.py        # Handle quote request workflow
│   ├── workspace_management.py    # Create/manage workspace folders
│   └── document_analysis.py       # Extract data from documents
│
├── adapters/                      # ADAPTERS LAYER
│   ├── __init__.py
│   ├── ms365_adapter.py           # Microsoft 365 / Graph API
│   ├── googlews_adapter.py        # Google Workspace / Gmail API
│   ├── database_adapter.py        # PostgreSQL queries
│   └── storage_adapter.py         # File storage (local/S3/etc.)
│
├── routes/                        # API ENDPOINTS
│   ├── ms365.py                   # Webhook receivers (adapter-level)
│   ├── googlews.py
│   └── processes.py               # Business endpoints (process-level)
│
├── workers/                       # BACKGROUND TASKS
│   └── webhook_worker.py          # Calls processes to handle events
│
└── models/                        # DATA MODELS
    ├── events.py                  # Event schemas
    └── processes.py               # Process schemas
```

---

## Example: Quote Request Workflow

### **n8n Workflow**
```
Trigger: New Email Event
  ↓
Node 1: Analyze Email (POST /api/processes/email/analyze)
  ↓
Node 2: Switch by Intent
  ├─ quote_request → Node 3
  ├─ invoice → Other workflow
  └─ general → Archive
  ↓
Node 3: Process Quote Request (POST /api/processes/quote/handle)
  Input: { event_id, folder_name, extract_attachments: true }
  Output: { folder_path, files_created: [...] }
```

### **Process Layer Implementation**
```python
# api/app/processes/quote_processing.py

from ..adapters import ms365_adapter, database_adapter, storage_adapter

async def handle_quote_request(event_id: str, folder_name: str) -> dict:
    """
    Business workflow: Process quote request email
    
    Steps:
    1. Get email from database (normalized_payload)
    2. Analyze intent and extract entities
    3. Download attachments from MS365
    4. Create workspace folder
    5. Write message.json, metadata.json
    6. Save attachments to folder
    """
    # Get event from database
    event = await database_adapter.get_webhook_event(event_id)
    
    # Extract message data from normalized_payload
    message = event['normalized_payload']['message']
    credential_id = event['credential_id']
    
    # Analyze content (AI classification)
    analysis = await analyze_email_content(message)
    
    # Download attachments via MS365 adapter
    attachments = []
    if message['has_attachments']:
        attachments = await ms365_adapter.download_attachments(
            credential_id, 
            message['id']
        )
    
    # Create workspace folder via storage adapter
    folder_path = await storage_adapter.create_workspace_folder(folder_name)
    
    # Write files
    await storage_adapter.write_json(f"{folder_path}/message.json", message)
    await storage_adapter.write_json(f"{folder_path}/metadata.json", analysis)
    
    # Save attachments
    for attachment in attachments:
        await storage_adapter.save_attachment(
            f"{folder_path}/attachments/{attachment['name']}", 
            attachment['content']
        )
    
    return {
        "folder_path": folder_path,
        "files_created": [
            "message.json",
            "metadata.json",
            f"attachments/{att['name']}" for att in attachments
        ]
    }
```

### **Adapter Layer Implementation**
```python
# api/app/adapters/ms365_adapter.py

from msgraph import GraphServiceClient
from ..services.auth_client import get_credential_token

async def download_attachments(credential_id: str, message_id: str) -> list:
    """
    Download all attachments from an MS365 email
    
    Returns list of: {name, content_type, size, content}
    """
    graph_client = await get_graph_client(credential_id)
    
    attachments = await graph_client.me.messages.by_message_id(message_id)\
        .attachments.get()
    
    results = []
    for attachment in attachments.value:
        results.append({
            "name": attachment.name,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "content": attachment.content_bytes  # Base64 decoded
        })
    
    return results
```

---

## API Endpoint Design

### **Process-Level Endpoints** (for n8n)
```python
# api/app/routes/processes.py

@router.post("/processes/email/analyze")
async def analyze_email(request: AnalyzeEmailRequest):
    """Classify email intent and extract entities"""
    return await email_classification.analyze(request.event_id)

@router.post("/processes/quote/handle")
async def handle_quote(request: QuoteRequestRequest):
    """Process quote request: create workspace, extract attachments"""
    return await quote_processing.handle_quote_request(
        request.event_id,
        request.folder_name
    )

@router.post("/processes/workspace/create")
async def create_workspace(request: WorkspaceRequest):
    """Create workspace folder with message and attachments"""
    return await workspace_management.create_workspace(
        request.event_id,
        request.folder_name,
        request.options
    )
```

### **Adapter-Level Endpoints** (webhooks, low-level)
```python
# api/app/routes/ms365.py

@router.post("/ms365/webhook")
async def receive_webhook(request: Request):
    """MS365 webhook receiver (adapter-level)"""
    # Store event, return 202
    pass

@router.post("/ms365/subscriptions")
async def create_subscription(request: CreateSubscriptionRequest):
    """Manage MS365 subscriptions (adapter-level)"""
    pass
```

---

## Benefits of This Architecture

### **1. Clear Separation of Concerns**
- **Process layer** = "What to do" (business logic)
- **Adapters layer** = "How to do it" (technical implementation)

### **2. Easy Testing**
- Mock adapters to test processes in isolation
- Test adapters independently with integration tests

### **3. Flexibility**
- Replace MS365 with different email provider? Only change adapter
- Change workspace storage from local to S3? Only change storage adapter

### **4. n8n Integration**
- n8n calls high-level process endpoints
- Process layer handles complexity, n8n stays simple

### **5. Extensibility**
- Add new processes (invoice processing, contract analysis)
- Add new adapters (Salesforce, Slack, etc.)

---

## Migration Plan

### **Phase 1: Refactor Existing Code**
1. Create `api/app/adapters/` directory
2. Move `ms365_service.py` → `ms365_adapter.py`
3. Update imports in existing code

### **Phase 2: Create Process Layer**
1. Create `api/app/processes/` directory
2. Implement `email_classification.py`
3. Implement `quote_processing.py`
4. Implement `workspace_management.py`

### **Phase 3: Add Process Endpoints**
1. Create `api/app/routes/processes.py`
2. Expose process-level APIs for n8n

### **Phase 4: Update Worker**
1. Modify `webhook_worker.py` to call process layer
2. Keep adapter calls for simple normalization

---

## Naming Conventions

### **Process Layer**
- Files: `{business_capability}.py` (e.g., `quote_processing.py`)
- Functions: `handle_*`, `process_*`, `analyze_*`
- Focus: Business workflow orchestration

### **Adapters Layer**
- Files: `{system}_adapter.py` (e.g., `ms365_adapter.py`)
- Functions: `get_*`, `create_*`, `fetch_*`, `download_*`
- Focus: Technical operations on external systems

### **Routes**
- Process routes: `/api/processes/{capability}/{action}`
- Adapter routes: `/api/{adapter}/{resource}` (webhooks, subscriptions)

---

## Future Considerations

### **AI/LangGraph Integration**
- Create `ai_adapter.py` for OpenAI, Anthropic, etc.
- Processes call `ai_adapter.classify()`, `ai_adapter.extract_entities()`

### **Event Streaming**
- Create `events_adapter.py` for Kafka, RabbitMQ
- Processes publish events, n8n subscribes

### **Observability**
- Process layer logs business events
- Adapter layer logs technical events
- Clear separation in monitoring dashboards

---

**This architecture provides a clean foundation for building Flovify's AI-powered workflow automation platform.**
