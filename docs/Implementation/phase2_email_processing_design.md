# Phase 2: Type-Agnostic Email Processing - Design Document

**Date**: 2025-11-15  
**Status**: Ready for Implementation  
**Estimated Duration**: 5-6 hours

---

## Overview

Implement a **type-agnostic email processing task** that serves as an n8n workflow node. The task performs mechanical operations without business logic - n8n provides all intelligence.

### **Design Philosophy**

- **API Task = Dumb Executor**: Fetch → Folder → Save → Move
- **n8n = Smart Orchestrator**: Classifies, extracts, decides, routes
- **Metadata = Flexible Bag**: Anything n8n provides is saved untouched

---

## Endpoint Specification

### **Request**

```
POST /api/processes/email/process-and-archive
```

**Body** (application/json):
```json
{
  "credential_id": "uuid",              // REQUIRED - MS365/Google credential
  "message_id": "email-id",             // REQUIRED - Email to process
  "customer_id": "C12345",              // REQUIRED - Business entity ID
  "customer_name": "Acme Corporation",  // REQUIRED - Display name
  "category": "Quotes",                 // REQUIRED - Folder under customer
  "ref_number": "QT-2025-1234",         // REQUIRED - Reference/tracking number
  "subject_synthetic": "Pump Request",  // REQUIRED - Clean subject for folder name
  "move_to_folder": "Quotes - Pending", // OPTIONAL - Target mailbox folder (null = don't move)
  "metadata": {                         // REQUIRED - Arbitrary data from n8n
    "email_type": "quote",
    "contact_name": "John Doe",
    "urgency": "high",
    "expected_response_days": 3,
    // ... any other fields
  }
}
```

### **Response - Success**

```json
{
  "status": "success",
  "workspace": {
    "relative_path": "Clients/C12345-Acme_Corporation/Quotes/QT-2025-1234-Pump_Request/",
    "absolute_url": "https://tenant.sharepoint.com/drive/root:/Clients/C12345-Acme_Corporation/..."
  },
  "files_created": [
    "email.json",
    "attachments/drawing.pdf",
    "attachments/specs.xlsx"
  ],
  "email_moved": {
    "from": "Inbox",
    "to": "Quotes - Pending"
  }
}
```

### **Response - Error**

```json
{
  "status": "error",
  "error_type": "AttachmentDownloadFailed",
  "message": "Failed to download attachment 'large-file.pdf': timeout after 30s",
  "context": {
    "credential_id": "uuid",
    "message_id": "email-id",
    "customer": "C12345-Acme Corporation",
    "attachment_name": "large-file.pdf",
    "workspace_path": "Clients/C12345-Acme_Corporation/Quotes/QT-2025-1234-Pump_Request/"
  }
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Invalid request (missing required field, invalid credential)
- 404: Email not found
- 500: Internal error (attachment download, folder creation, email move failure)

---

## Folder Structure

### **Pattern (Fixed)**

```
/Clients/{customer_id}-{sanitized_customer_name}/{category}/{ref_number}-{sanitized_subject}/
```

**Example Paths**:
- Quote: `/Clients/C12345-Acme_Corp/Quotes/QT-2025-1234-Industrial_Pump_Request/`
- Support: `/Clients/C12345-Acme_Corp/Support/TK-5678-Login_Issue_Report/`
- Project: `/Clients/C67890-Beta_Inc/Projects/PJ-9012-New_Facility_Design/`
- Custom: `/Clients/C99999-Gamma_LLC/Legal/CONTRACT-2025-42-NDA_Review/`

### **Sanitization Rules**

- Remove special chars: `/ \ : * ? " < > |`
- Replace spaces with underscores
- Replace multiple underscores with single
- Truncate to 100 chars max
- Trim leading/trailing underscores

**Examples**:
- `"Acme Corporation Inc."` → `Acme_Corporation_Inc`
- `"John's: Quote #42 (urgent!)"` → `Johns_Quote_42_urgent`
- `"Re: Re: Fwd: Need help ASAP!!!"` → `Re_Re_Fwd_Need_help_ASAP`

### **Folder Creation Behavior**

- **Auto-create entire path** if any folder doesn't exist
- No errors if folders already exist (idempotent)
- Permissions inherited from parent folder

---

## email.json Structure

### **Complete Format**

```json
{
  "metadata": {
    // UNTOUCHED PASSTHROUGH from request.metadata
    "email_type": "quote",
    "contact_name": "John Doe",
    "urgency": "high",
    "expected_response_days": 3,
    "requires_technical_review": true,
    // ... any other fields n8n provides
  },
  
  "processing_info": {
    // SYSTEM-ADDED metadata
    "processed_at": "2025-11-15T14:30:00Z",
    "credential_id": "uuid",
    "workspace_path": "Clients/C12345-Acme_Corp/Quotes/QT-2025-1234-Pump_Request/",
    "workspace_url": "https://tenant.sharepoint.com/...",
    "processor_version": "0.2.0"
  },
  
  "email": {
    // NORMALIZED email data from adapter (platform-agnostic format)
    "id": "AAMkAGI2...",
    "subject": "Re: Need quote for industrial pump ASAP!!!",
    "from": {
      "name": "John Doe",
      "address": "jdoe@acmecorp.com"
    },
    "to": [{"name": "...", "address": "..."}],
    "cc": [],
    "bcc": [],
    "received_at": "2025-11-15T14:25:00Z",
    "body_preview": "We need a quote for...",
    "body_content": "<html>...",
    "body_type": "html",
    "has_attachments": true,
    "is_read": true,
    "importance": "high"
  },
  
  "attachments": [
    {
      "name": "drawing.pdf",
      "size": 245678,
      "content_type": "application/pdf",
      "saved_path": "attachments/drawing.pdf"
    },
    {
      "name": "specifications.xlsx",
      "size": 89456,
      "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "saved_path": "attachments/specifications.xlsx"
    }
  ]
}
```

---

## Implementation Architecture

### **Process Layer Function**

**File**: `api/app/processes/email_processing.py`

```python
async def process_and_archive_email(
    credential_id: str,
    message_id: str,
    customer_id: str,
    customer_name: str,
    category: str,
    ref_number: str,
    subject_synthetic: str,
    move_to_folder: Optional[str],
    metadata: dict
) -> dict
```

**Steps**:
1. Fetch email via mail adapter
2. Build folder path with sanitization
3. Create folder on Drive (auto-create full path)
4. Build email.json with metadata passthrough
5. Download each attachment via mail adapter
6. Upload each attachment to Drive
7. Upload email.json to Drive
8. Move email to target folder (if specified)
9. Get absolute Drive URL
10. Return workspace info

**Error Handling**:
- Any failure raises exception with context
- Exception propagates to endpoint for HTTP error response
- No partial state (no files saved if any step fails)

---

### **Required Adapter Primitives**

#### **MS365 Mail Adapter** (`adapters/ms365/mail.py`)

**Existing**:
- ✅ `get_message(credential_id, message_id) -> dict`
- ✅ `list_messages(credential_id, folder, limit, filter_query) -> list`

**New**:
- ➕ `download_attachment(credential_id, message_id, attachment_id) -> bytes`
- ➕ `move_message(credential_id, message_id, target_folder: str) -> dict`

#### **MS365 Drive Adapter** (`adapters/ms365/drive.py`) - NEW FILE

- ➕ `ensure_folder_path(credential_id, path: str) -> str` 
  - Creates all folders in path if don't exist
  - Returns absolute OneDrive URL
  
- ➕ `upload_file(credential_id, path: str, content: bytes) -> None`
  - Creates parent folders if needed
  - Overwrites if file exists
  
- ➕ `upload_json(credential_id, path: str, data: dict) -> None`
  - Serializes dict to JSON
  - Calls upload_file with JSON bytes
  
- ➕ `get_folder_url(credential_id, path: str) -> str`
  - Returns absolute OneDrive/SharePoint URL for folder

---

## n8n Integration Pattern

### **Example Workflow: Quote Request**

```
┌─────────────────────────────────────────────────┐
│ 1. MS365 Webhook Trigger                       │
│    Event: New email in Inbox                   │
│    Output: { message_id, from, subject, ... }  │
├─────────────────────────────────────────────────┤
│ 2. AI Agent: Classify Email Type               │
│    Input: Email subject + body preview         │
│    Output: { email_type: "quote" }             │
├─────────────────────────────────────────────────┤
│ 3. Switch Node (on email_type)                 │
│    Case "quote": Continue                      │
│    Case "support": Different path              │
│    Default: Archive to General                 │
├─────────────────────────────────────────────────┤
│ 4. AI Agent: Extract Customer Info             │
│    Input: Email body                           │
│    Output: {                                    │
│      customer_id: "C12345",                     │
│      customer_name: "Acme Corp",                │
│      contact_name: "John Doe",                  │
│      urgency: "high"                            │
│    }                                            │
├─────────────────────────────────────────────────┤
│ 5. Set Variables                                │
│    ref_number = "QT-" + {{ $now.format('YYYY') }} + "-" + {{ generateSeq() }}│
│    category = "Quotes"                          │
│    move_to_folder = "Quotes - Pending"          │
├─────────────────────────────────────────────────┤
│ 6. AI Agent: Generate Synthetic Subject        │
│    Input: Original subject                      │
│    Output: { subject_synthetic: "Industrial Pump Quotation" }│
├─────────────────────────────────────────────────┤
│ 7. HTTP Request Node                            │
│    Method: POST                                 │
│    URL: https://api.flovify.ca/api/processes/email/process-and-archive│
│    Body: {                                      │
│      credential_id: "{{ $vars.ms365_cred }}",   │
│      message_id: "{{ $webhook.message_id }}",   │
│      customer_id: "{{ $node.Extract.customer_id }}",│
│      customer_name: "{{ $node.Extract.customer_name }}",│
│      category: "Quotes",                        │
│      ref_number: "{{ $node.SetVars.ref_number }}",│
│      subject_synthetic: "{{ $node.AI.subject_synthetic }}",│
│      move_to_folder: "Quotes - Pending",        │
│      metadata: {                                │
│        email_type: "quote",                     │
│        contact_name: "{{ $node.Extract.contact_name }}",│
│        urgency: "{{ $node.Extract.urgency }}",  │
│        expected_response_days: 3                │
│      }                                          │
│    }                                            │
│    Output: { workspace, files_created, ... }   │
├─────────────────────────────────────────────────┤
│ 8. Notify Sales Team (Slack/Email)             │
│    Message: "New quote request from {{ customer_name }}"│
│    Link: "{{ $node.HTTP.workspace.absolute_url }}"│
└─────────────────────────────────────────────────┘
```

---

## Testing Strategy

### **Unit Tests**

Test adapters with mocked MS Graph API:
- Mail adapter: download_attachment, move_message
- Drive adapter: ensure_folder_path, upload_file, upload_json

Test process function with mocked adapters:
- Successful flow with attachments
- Successful flow without attachments
- Error handling for each step

### **Integration Tests**

Test with real MS365 account (test tenant):
1. Send test email with attachments to inbox
2. Call endpoint with valid parameters
3. Verify folder created on OneDrive
4. Verify email.json exists and has correct structure
5. Verify attachments downloaded and uploaded
6. Verify email moved to target folder

### **Error Scenario Tests**

- Invalid credential_id → 400 error
- Non-existent message_id → 404 error
- Attachment download timeout → 500 error with context
- Folder creation permission denied → 500 error with context
- Email already in target folder → Should not error (idempotent)

---

## Deployment Checklist

- [ ] Implement MS365 mail adapter primitives
- [ ] Implement MS365 drive adapter (new file)
- [ ] Implement process function
- [ ] Implement process endpoint with Pydantic models
- [ ] Write unit tests
- [ ] Test locally with real MS365 account
- [ ] Update API documentation (OpenAPI/Swagger)
- [ ] Commit and push to GitHub
- [ ] Deploy to VPS
- [ ] Test end-to-end on production
- [ ] Create example n8n workflow template

---

## Future Enhancements (Out of Scope for Phase 2)

- Google Workspace support (Phase 5)
- Attachment virus scanning
- Large attachment streaming (>10MB)
- Folder permission management
- Automatic folder archiving (old quotes)
- Email thread grouping
- Duplicate detection
- Attachment OCR/preview generation
- Integration with external systems (ERP, CRM)

---

## Success Criteria

✅ Type-agnostic design (no hardcoded email types)  
✅ Metadata passthrough works (n8n data preserved)  
✅ Folder structure consistent and predictable  
✅ Error responses include full context  
✅ Works with MS365 OneDrive  
✅ n8n can use as generic workflow node  
✅ Any failure = entire task fails (no partial state)  
✅ Returns both relative path and absolute URL  

---

**Ready for Implementation**: Yes  
**Next Step**: Implement MS365 mail adapter primitives (download_attachment, move_message)
