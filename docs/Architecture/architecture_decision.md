# Flovify API Architecture: Process + Adapters

**Date**: 2025-11-15  
**Status**: Approved - Implementation Pending  
**Version**: 1.0

---

## Executive Summary

Flovify API implements a **two-layer architecture** separating business workflows from technical integrations:

- **Process Layer**: Business workflows (quote processing, email classification)
- **Adapters Layer**: External system integrations (MS365, Google Workspace, database, storage)

This architecture enables:
- **Platform-agnostic** business logic (works with MS365, Google, or future providers)
- **Clean separation** of concerns (business vs technical)
- **Easy testing** (mock adapters, test processes in isolation)
- **Extensibility** (add new providers or workflows independently)

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         n8n Workflows                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Trigger → Analyze → Route by Type → Process Quote         │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP API Calls
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PROCESS LAYER (Business)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  api/app/processes/                                         │ │
│  │  ├── email_classification.py  (Classify intent)            │ │
│  │  ├── quote_processing.py      (Handle quote requests)      │ │
│  │  ├── workspace_management.py  (Create folders)             │ │
│  │  └── document_analysis.py     (Extract data)               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Responsibilities:                                               │
│  - Orchestrate multi-step workflows                             │
│  - Apply business rules and validation                          │
│  - Coordinate adapters to achieve goals                         │
│  - Provide high-level APIs for n8n                              │
└────────────────────────────┬─────────────────────────────────────┘
                             │ Uses
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   ADAPTERS LAYER (Technical)                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  api/app/adapters/                                          │ │
│  │  ├── ms365/              (Microsoft 365 integration)        │ │
│  │  │   ├── mail.py         • get_message()                    │ │
│  │  │   ├── drive.py        • create_folder()                  │ │
│  │  │   └── calendar.py     • get_events()                     │ │
│  │  │                                                           │ │
│  │  ├── googlews/           (Google Workspace integration)     │ │
│  │  │   ├── mail.py         • get_message()                    │ │
│  │  │   ├── drive.py        • create_folder()                  │ │
│  │  │   └── calendar.py     • get_events()                     │ │
│  │  │                                                           │ │
│  │  ├── database.py         (PostgreSQL queries)               │ │
│  │  └── storage.py          (File operations)                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Responsibilities:                                               │
│  - Wrap third-party APIs (msgraph-sdk, google-api)             │
│  - Handle authentication, retries, rate limiting                │
│  - Normalize data formats from different providers             │
│  - Provide consistent interfaces to Process layer              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              EXTERNAL SYSTEMS (Third-party APIs)                 │
│  ├── Microsoft Graph API                                         │
│  ├── Google Workspace APIs (Gmail, Drive, Calendar)             │
│  ├── PostgreSQL Database                                         │
│  └── Local/Cloud Storage (filesystem, S3, Azure Blob)           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer Definitions

### **Process Layer** (`api/app/processes/`)

**Purpose**: Implement business workflows that solve real-world problems

**Characteristics**:
- **Business-focused**: Speaks in domain language (quotes, invoices, workspaces)
- **Provider-agnostic**: Doesn't care if email comes from MS365 or Google
- **Orchestration**: Coordinates multiple adapters to complete workflows
- **Stateless**: Pure functions that use adapters for I/O

**Example Files**:
```
processes/
├── email_classification.py      # "Is this a quote request or invoice?"
├── quote_processing.py          # "Process a quote request end-to-end"
├── workspace_management.py      # "Create folder with message + attachments"
└── document_analysis.py         # "Extract data from document"
```

**Example Function**:
```python
async def handle_quote_request(event_id: str, folder_name: str) -> dict:
    """
    Business workflow: Process quote request email
    
    Steps:
    1. Get email from database
    2. Classify intent
    3. Download attachments (uses mail adapter)
    4. Create workspace folder (uses storage adapter)
    5. Write files
    
    Returns: {"folder_path": "...", "files_created": [...]}
    """
```

---

### **Adapters Layer** (`api/app/adapters/`)

**Purpose**: Provide clean, consistent interfaces to external systems

**Characteristics**:
- **Technical**: Deals with APIs, authentication, error codes
- **Provider-specific**: One adapter per external system
- **Primitive operations**: Atomic actions like "get message", "create folder"
- **Normalized output**: Consistent data format regardless of provider

**Organization**:
```
adapters/
├── ms365/                  # Microsoft 365 adapter
│   ├── mail.py            # Email primitives
│   ├── drive.py           # OneDrive/SharePoint primitives
│   └── _auth.py           # MS365 authentication (internal)
│
├── googlews/               # Google Workspace adapter
│   ├── mail.py            # Gmail primitives
│   ├── drive.py           # Google Drive primitives
│   └── _auth.py           # Google OAuth (internal)
│
├── database.py             # PostgreSQL primitives
└── storage.py              # File system primitives
```

**Example Primitive**:
```python
async def get_message(credential_id: str, message_id: str) -> dict:
    """
    Get email message (provider-specific implementation)
    
    Returns normalized format:
    {
        "id": "...",
        "subject": "...",
        "from": {"name": "...", "email": "..."},
        "received_at": "2025-11-15T10:30:00Z",
        "body": "...",
        "has_attachments": true
    }
    """
```

---

## Terminology

| Term | Definition | Examples |
|------|------------|----------|
| **Adapter** | Integration with external system/provider | `ms365`, `googlews`, `database`, `storage` |
| **Service** | Functional capability within an adapter | `mail`, `drive`, `calendar` |
| **Primitive** | Atomic operation on a service | `get_message()`, `create_folder()`, `send_email()` |
| **Process** | Business workflow that uses adapters | `quote_processing`, `email_classification` |
| **Workflow** | Multi-step process with business logic | "Handle quote request: analyze → download → create workspace" |

---

## Adapter Organization: Provider → Service → Primitives

### **Structure**

```
adapters/
├── {provider}/              # e.g., ms365, googlews
│   ├── __init__.py         # Exports services
│   ├── {service}.py        # e.g., mail, drive, calendar
│   └── _auth.py            # Provider-specific authentication (internal)
```

### **Example: MS365 Adapter**

```python
# adapters/ms365/mail.py
"""MS365 Mail Service: Email primitives for Microsoft 365"""

async def get_message(credential_id: str, message_id: str) -> dict:
    """Fetch single email message"""
    pass

async def list_messages(credential_id: str, folder: str = "inbox", limit: int = 50) -> list:
    """List messages in folder"""
    pass

async def send_message(credential_id: str, to: str, subject: str, body: str) -> str:
    """Send email, returns message_id"""
    pass

async def move_message(credential_id: str, message_id: str, folder_id: str) -> bool:
    """Move message to folder"""
    pass

async def download_attachments(credential_id: str, message_id: str) -> list:
    """Download all attachments, returns list of {name, content, type}"""
    pass
```

### **Example: Google Workspace Adapter (Same Interface!)**

```python
# adapters/googlews/mail.py
"""Google Workspace Mail Service: Email primitives for Gmail"""

async def get_message(credential_id: str, message_id: str) -> dict:
    """Fetch single email message (Gmail implementation)"""
    pass

async def list_messages(credential_id: str, folder: str = "inbox", limit: int = 50) -> list:
    """List messages in folder (Gmail labels)"""
    pass

async def send_message(credential_id: str, to: str, subject: str, body: str) -> str:
    """Send email via Gmail, returns message_id"""
    pass

# ... same signatures as MS365!
```

**Key Point**: Process layer calls `mail.get_message()` - doesn't care if it's MS365 or Google!

---

## API Endpoint Organization

### **Process-Level Endpoints** (for n8n)

```
POST /api/processes/email/analyze
POST /api/processes/quote/handle
POST /api/processes/workspace/create
GET  /api/processes/events/pending
```

**Purpose**: High-level business operations for n8n workflows

**Example**:
```bash
# n8n calls this to process a quote request
curl -X POST /api/processes/quote/handle \
  -d '{"event_id": "abc-123", "folder_name": "Quote_JohnDoe"}'

# Returns: {"folder_path": "...", "files_created": ["message.json", "attachments/img1.jpg"]}
```

---

### **Adapter-Level Endpoints** (webhooks, low-level)

```
POST /api/ms365/webhook              # Receive MS365 notifications
POST /api/ms365/subscriptions        # Manage subscriptions
POST /api/googlews/webhook           # Receive Google notifications
```

**Purpose**: Technical endpoints for external systems, not for n8n

---

## Data Flow Example: Quote Request Workflow

### **Scenario**
User sends email with quote request → n8n processes → Flovify creates workspace folder

### **Step-by-Step**

```
1. MS365 sends webhook notification
   POST /api/ms365/webhook
   └─> Stores in webhook_events table (status=pending)

2. Background worker processes event
   webhook_worker.py
   ├─> Fetches full message via ms365.mail.get_message()
   ├─> Normalizes to standard format
   └─> Updates status=completed

3. n8n polls for new events
   GET /api/processes/events/pending
   └─> Returns events with normalized_payload

4. n8n analyzes email
   POST /api/processes/email/analyze
   └─> Process: email_classification.analyze_email()
       └─> Returns: {intent: "quote_request", confidence: 0.95}

5. n8n routes to quote workflow
   POST /api/processes/quote/handle
   └─> Process: quote_processing.handle_quote_request()
       ├─> Adapter: database.get_webhook_event()
       ├─> Adapter: ms365.mail.download_attachments()
       ├─> Adapter: storage.create_workspace_folder()
       ├─> Adapter: storage.write_json() (message.json, metadata.json)
       └─> Adapter: storage.save_attachment() (images)
       
6. Result: Folder created
   /workspace/Quote_JohnDoe_2025-11-15/
   ├── message.json
   ├── metadata.json
   └── attachments/
       ├── image1.jpg
       └── image2.jpg
```

---

## Benefits of This Architecture

### **1. Platform Agnostic**
- Process layer works with MS365, Google, or any future provider
- Switch providers by changing adapter, not business logic
- Example: Move from MS365 to Google → only adapter changes

### **2. Testable**
```python
# Mock adapters in tests
from unittest.mock import AsyncMock
from processes import quote_processing
from adapters import ms365

# Mock MS365 adapter
ms365.mail.get_message = AsyncMock(return_value={"subject": "Test Quote"})

# Test process without hitting real MS365
result = await quote_processing.handle_quote_request("event-123")
assert result["folder_path"] == "/workspace/Quote_Test"
```

### **3. Maintainable**
- Clear boundaries: business vs technical
- Each layer has single responsibility
- Easy to find code: "mail sending" → `adapters/{provider}/mail.py`

### **4. Extensible**
```python
# Add Salesforce adapter
adapters/salesforce/
├── contacts.py       # get_contact(), create_contact()
└── opportunities.py  # get_opportunity(), create_opportunity()

# Process layer can now use Salesforce
from adapters.salesforce import contacts
customer = await contacts.get_contact(email="john@example.com")
```

### **5. n8n Integration**
- n8n calls simple, high-level process endpoints
- Complexity hidden in process layer
- n8n workflows stay clean and understandable

---

## Design Principles

### **Process Layer Principles**

1. **Business Language**: Functions named after business operations
   - ✅ `handle_quote_request()`
   - ❌ `process_ms365_message()`

2. **Provider Agnostic**: Never import provider-specific libraries
   - ✅ `from adapters import mail`
   - ❌ `from msgraph import GraphServiceClient`

3. **Orchestration**: Coordinate adapters, don't do I/O directly
   - ✅ `message = await mail.get_message()`
   - ❌ `message = GraphServiceClient().me.messages.get()`

4. **Pure Functions**: Take inputs, return outputs, side effects via adapters
   ```python
   async def handle_quote_request(event_id: str) -> dict:
       # Good: Uses adapters for I/O
       event = await database.get_webhook_event(event_id)
       message = await mail.get_message(credential_id, message_id)
       return {"status": "success"}
   ```

### **Adapter Layer Principles**

1. **Provider-Specific**: One adapter per external system
   - `adapters/ms365/` - MS365 only
   - `adapters/googlews/` - Google only

2. **Primitive Operations**: Atomic, single-purpose functions
   - ✅ `get_message(message_id)` - one thing
   - ❌ `process_quote_request()` - too high-level

3. **Normalized Output**: Consistent format across providers
   ```python
   # Both MS365 and Google return same structure
   {
       "id": "...",
       "subject": "...",
       "from": {"name": "...", "email": "..."},
       "received_at": "ISO 8601 timestamp"
   }
   ```

4. **Hide Complexity**: Handle auth, retries, errors internally
   ```python
   async def get_message(credential_id, message_id):
       # Handles: token vending, retries, error codes
       # Returns: clean data or raises exception
   ```

---

## File Organization

```
api/app/
├── processes/                        # BUSINESS LAYER
│   ├── __init__.py
│   ├── email_classification.py
│   ├── quote_processing.py
│   ├── workspace_management.py
│   └── document_analysis.py
│
├── adapters/                         # TECHNICAL LAYER
│   ├── __init__.py
│   │
│   ├── ms365/                        # Microsoft 365 Adapter
│   │   ├── __init__.py              # Exports: mail, drive, calendar
│   │   ├── mail.py                  # Email primitives
│   │   ├── drive.py                 # OneDrive/SharePoint primitives
│   │   ├── calendar.py              # Calendar primitives
│   │   └── _auth.py                 # MS365 auth (internal, not exported)
│   │
│   ├── googlews/                     # Google Workspace Adapter
│   │   ├── __init__.py              # Exports: mail, drive, calendar
│   │   ├── mail.py                  # Gmail primitives
│   │   ├── drive.py                 # Google Drive primitives
│   │   ├── calendar.py              # Google Calendar primitives
│   │   └── _auth.py                 # Google auth (internal)
│   │
│   ├── database.py                   # Database primitives
│   └── storage.py                    # File storage primitives
│
├── routes/                           # API ENDPOINTS
│   ├── ms365.py                     # Webhook receiver (adapter-level)
│   ├── googlews.py                  # Webhook receiver
│   └── processes.py                 # Business endpoints (process-level)
│
├── workers/                          # BACKGROUND TASKS
│   └── webhook_worker.py            # Event processor
│
├── models/                           # DATA SCHEMAS
│   ├── events.py                    # Webhook event models
│   └── processes.py                 # Process request/response models
│
└── services/                         # INTERNAL UTILITIES
    ├── auth_client.py               # Token vending client
    ├── database.py                  # DB connection utilities
    └── migrations.py                # Migration runner
```

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Process Layer | ⏳ Planned | To be implemented |
| Adapters: MS365 Mail | ✅ Partial | Exists as `services/ms365_service.py`, needs refactor |
| Adapters: MS365 Drive | ⏳ Planned | To be implemented |
| Adapters: GoogleWS | ⏳ Planned | Auth exists, services needed |
| Adapters: Database | ⏳ Planned | Basic utilities exist |
| Adapters: Storage | ⏳ Planned | To be implemented |
| Process Endpoints | ⏳ Planned | To be implemented |
| Webhook System | ✅ Complete | Working (receiver + worker) |

---

## Next Steps

See companion documents:
- `refactor_plan.md` - Step-by-step refactoring instructions
- `platform_agnostic_processes.md` - Python patterns for provider abstraction

---

**This architecture provides a solid foundation for building Flovify's AI-powered workflow automation platform with clean separation of business and technical concerns.**
