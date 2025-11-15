# Platform-Agnostic Processes: Python Implementation Patterns

**Date**: 2025-11-15  
**Audience**: Developers (including Python beginners)  
**Goal**: Explain how Python implements platform-agnostic business logic

---

## The Problem

**Question**: How do processes work with both MS365 and Google without knowing which provider they're using?

**Example Scenario**:
```python
# Process should work regardless of email provider
async def handle_quote_request(event_id: str):
    # How does this know if it's MS365 or Google?
    message = await ???.get_message(credential_id, message_id)
    
    # We want ONE process that works for BOTH providers
```

---

## The Solution: Dependency Injection (DI)

### **What is Dependency Injection?**

Instead of the process **creating** its dependencies (adapters), we **pass them in** from outside.

**Bad (Tightly Coupled)**:
```python
async def handle_quote_request(event_id: str):
    # Process decides which adapter to use - HARD-CODED!
    from adapters.ms365 import mail
    message = await mail.get_message(...)  # Only works with MS365!
```

**Good (Loosely Coupled)**:
```python
async def handle_quote_request(event_id: str, mail_adapter):
    # Process uses whatever adapter you give it
    message = await mail_adapter.get_message(...)  # Works with ANY adapter!
```

---

## Python Patterns for Abstraction

Python offers several ways to achieve platform-agnostic code:

### **Pattern 1: Duck Typing** (Pythonic, Recommended) ⭐⭐⭐

**Concept**: "If it walks like a duck and quacks like a duck, it's a duck"

Python doesn't require formal interfaces. As long as the adapter has the right methods, it works!

```python
# Process doesn't care about types, just that methods exist
async def handle_quote_request(event_id: str, mail_adapter):
    """
    Works with ANY adapter that has get_message() method
    
    mail_adapter could be:
    - adapters.ms365.mail
    - adapters.googlews.mail
    - A mock in tests
    """
    message = await mail_adapter.get_message(credential_id, message_id)
    # Process continues...
```

**Both adapters implement same methods**:
```python
# adapters/ms365/mail.py
async def get_message(credential_id, message_id):
    # MS365 implementation using Graph API
    pass

# adapters/googlews/mail.py
async def get_message(credential_id, message_id):
    # Google implementation using Gmail API
    pass
```

**Usage**:
```python
from adapters.ms365 import mail as ms365_mail
from adapters.googlews import mail as google_mail

# Same process, different adapters
result1 = await handle_quote_request(event_id, ms365_mail)
result2 = await handle_quote_request(event_id, google_mail)
```

**Pros**:
- Simple, Pythonic
- No extra code needed
- Flexible (works with any object with right methods)

**Cons**:
- No compile-time checking (won't know if method missing until runtime)
- Documentation important (developers need to know expected interface)

---

### **Pattern 2: Protocol (Type Hints)** ⭐⭐

**Concept**: Define expected interface using Python's `Protocol` (like interfaces in other languages)

```python
from typing import Protocol

class MailAdapter(Protocol):
    """Interface that all mail adapters must implement"""
    
    async def get_message(self, credential_id: str, message_id: str) -> dict:
        """Fetch single email message"""
        ...
    
    async def list_messages(self, credential_id: str, folder: str, limit: int) -> list:
        """List messages in folder"""
        ...
    
    async def send_message(self, credential_id: str, to: str, subject: str, body: str) -> str:
        """Send email, return message ID"""
        ...
```

**Process with type hints**:
```python
async def handle_quote_request(
    event_id: str, 
    mail_adapter: MailAdapter  # Type hint shows expected interface
) -> dict:
    message = await mail_adapter.get_message(credential_id, message_id)
    # IDE will autocomplete and type-check!
```

**Adapters implicitly satisfy protocol** (no inheritance needed):
```python
# adapters/ms365/mail.py
# No need to explicitly implement MailAdapter
# Just having the methods is enough!
async def get_message(credential_id: str, message_id: str) -> dict:
    pass

async def list_messages(credential_id: str, folder: str, limit: int) -> list:
    pass
```

**Pros**:
- Type checking in IDE
- Clear documentation of expected interface
- No runtime overhead (types removed at runtime)

**Cons**:
- Requires Python 3.8+ (`typing.Protocol`)
- More boilerplate code

---

### **Pattern 3: Abstract Base Class (ABC)** ⭐

**Concept**: Define formal base class that adapters must inherit from

```python
from abc import ABC, abstractmethod

class MailAdapter(ABC):
    """Abstract base class for mail adapters"""
    
    @abstractmethod
    async def get_message(self, credential_id: str, message_id: str) -> dict:
        """Fetch single email message"""
        pass
    
    @abstractmethod
    async def list_messages(self, credential_id: str, folder: str, limit: int) -> list:
        """List messages in folder"""
        pass
```

**Adapters must inherit**:
```python
# adapters/ms365/mail.py
from api.app.adapters.base import MailAdapter

class MS365Mail(MailAdapter):
    async def get_message(self, credential_id: str, message_id: str) -> dict:
        # Implementation
        pass
    
    async def list_messages(self, credential_id: str, folder: str, limit: int) -> list:
        # Implementation
        pass
```

**Usage**:
```python
ms365_mail = MS365Mail()
result = await handle_quote_request(event_id, ms365_mail)
```

**Pros**:
- Enforces implementation (can't create adapter without methods)
- Explicit inheritance shows relationship

**Cons**:
- More boilerplate (classes, inheritance)
- Less flexible (adapter MUST inherit)
- Not as Pythonic

---

### **Pattern 4: Adapter Factory** (Optional)

**Concept**: Factory function that returns the right adapter based on provider

```python
# adapters/factory.py
def get_mail_adapter(provider: str):
    """Return mail adapter for given provider"""
    if provider == "ms365":
        from .ms365 import mail
        return mail
    elif provider == "googlews":
        from .googlews import mail
        return mail
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

**Process uses factory**:
```python
async def handle_quote_request(event_id: str):
    # Get event to determine provider
    event = await database.get_webhook_event(event_id)
    
    # Get correct adapter
    mail_adapter = get_mail_adapter(event['provider'])
    
    # Use adapter
    message = await mail_adapter.get_message(
        event['credential_id'],
        event['external_resource_id']
    )
```

**Pros**:
- Process doesn't need to know about providers
- Centralized adapter selection logic

**Cons**:
- Extra indirection
- Factory needs updating for new providers

---

## Recommended Approach for Flovify

### **Hybrid: Duck Typing + Protocol Type Hints** ⭐⭐⭐

**Why?**
- Duck typing: Simple, Pythonic, minimal boilerplate
- Protocol: Type hints for IDE support, documentation

**Implementation**:

**Step 1: Define Protocol** (optional, for type hints)
```python
# api/app/adapters/protocols.py
from typing import Protocol

class MailAdapter(Protocol):
    """Mail adapter interface - all providers must implement"""
    
    async def get_message(self, credential_id: str, message_id: str) -> dict: ...
    async def list_messages(self, credential_id: str, folder: str, limit: int) -> list: ...
    async def send_message(self, credential_id: str, to: str, subject: str, body: str) -> str: ...
    async def download_attachments(self, credential_id: str, message_id: str) -> list: ...

class DriveAdapter(Protocol):
    """Drive adapter interface"""
    
    async def create_folder(self, credential_id: str, parent_id: str, name: str) -> str: ...
    async def upload_file(self, credential_id: str, folder_id: str, name: str, content: bytes) -> str: ...
    async def list_files(self, credential_id: str, folder_id: str) -> list: ...
```

**Step 2: Implement Adapters** (no inheritance, just match interface)
```python
# adapters/ms365/mail.py
async def get_message(credential_id: str, message_id: str) -> dict:
    """MS365 implementation"""
    pass

async def list_messages(credential_id: str, folder: str, limit: int) -> list:
    """MS365 implementation"""
    pass

# adapters/googlews/mail.py
async def get_message(credential_id: str, message_id: str) -> dict:
    """Google implementation"""
    pass

async def list_messages(credential_id: str, folder: str, limit: int) -> list:
    """Google implementation"""
    pass
```

**Step 3: Process Uses Type Hints** (optional)
```python
# processes/quote_processing.py
from ..adapters.protocols import MailAdapter, DriveAdapter

async def handle_quote_request(
    event_id: str,
    folder_name: str = None,
    extract_attachments: bool = True
) -> dict:
    """
    Process quote request (works with any provider)
    """
    # Get event from database
    from ..adapters import database
    event = await database.get_webhook_event(event_id)
    
    # Get appropriate adapters based on provider
    if event['provider'] == 'ms365':
        from ..adapters.ms365 import mail, drive
    elif event['provider'] == 'googlews':
        from ..adapters.googlews import mail, drive
    else:
        raise ValueError(f"Unsupported provider: {event['provider']}")
    
    # Use adapters (type hints show expected methods)
    message = await mail.get_message(
        event['credential_id'],
        event['external_resource_id']
    )
    
    attachments = await mail.download_attachments(
        event['credential_id'],
        event['external_resource_id']
    )
    
    # ... rest of process
```

---

## Complete Example: Platform-Agnostic Quote Processing

```python
# api/app/processes/quote_processing.py

from datetime import datetime
from typing import Optional

async def handle_quote_request(
    event_id: str,
    folder_name: Optional[str] = None,
    extract_attachments: bool = True
) -> dict:
    """
    Process quote request email: Create workspace with message + attachments
    
    PLATFORM AGNOSTIC: Works with MS365, Google, or future providers
    
    Args:
        event_id: Webhook event UUID
        folder_name: Custom folder name (auto-generated if None)
        extract_attachments: Whether to download attachments
        
    Returns:
        {
            "folder_path": "/workspace/Quote_JohnDoe_2025-11-15",
            "files_created": ["message.json", "metadata.json", "attachments/img1.jpg"]
        }
    """
    # Import adapters
    from ..adapters import database, storage
    
    # Get event from database
    event = await database.get_webhook_event(event_id)
    if not event:
        raise ValueError(f"Event {event_id} not found")
    
    # Get message from normalized payload
    message = event['normalized_payload']['message']
    credential_id = event['credential_id']
    provider = event['provider']
    
    # Get provider-specific mail adapter
    if provider == 'ms365':
        from ..adapters.ms365 import mail
    elif provider == 'googlews':
        from ..adapters.googlews import mail
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    # Generate folder name if not provided
    if not folder_name:
        from_name = message['from'].get('name', 'Unknown').replace(' ', '_')
        date_str = datetime.now().strftime('%Y-%m-%d')
        folder_name = f"Quote_{from_name}_{date_str}"
    
    # Create workspace folder
    folder_path = await storage.create_workspace_folder(folder_name)
    
    # Write message.json
    await storage.write_json(f"{folder_path}/message.json", message)
    
    # Analyze email (classification)
    from . import email_classification
    analysis = await email_classification.analyze_email(event_id)
    await storage.write_json(f"{folder_path}/metadata.json", analysis)
    
    files_created = ["message.json", "metadata.json"]
    
    # Download and save attachments
    if extract_attachments and message.get('has_attachments'):
        # Use provider-specific adapter (but same interface!)
        attachments = await mail.download_attachments(
            credential_id,
            message['id']
        )
        
        for attachment in attachments:
            file_path = f"{folder_path}/attachments/{attachment['name']}"
            await storage.save_attachment(file_path, attachment['content'])
            files_created.append(f"attachments/{attachment['name']}")
    
    return {
        "folder_path": folder_path,
        "files_created": files_created,
        "message_subject": message['subject'],
        "provider": provider
    }
```

**Key Points**:
1. Process imports `database` and `storage` adapters (provider-agnostic)
2. Process determines provider from event data
3. Process imports correct mail adapter based on provider
4. Process calls same methods regardless of provider (`mail.download_attachments`)
5. All adapters return normalized data format

---

## Testing Platform-Agnostic Code

### **Unit Tests with Mocks**

```python
# tests/test_processes/test_quote_processing.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from api.app.processes import quote_processing

@pytest.mark.asyncio
async def test_handle_quote_request_ms365():
    """Test quote processing with MS365"""
    
    # Mock database adapter
    mock_event = {
        "id": "event-123",
        "credential_id": "cred-456",
        "provider": "ms365",
        "normalized_payload": {
            "message": {
                "id": "msg-789",
                "subject": "Quote Request",
                "from": {"name": "John Doe", "email": "john@example.com"},
                "has_attachments": True
            }
        }
    }
    
    # Mock adapters
    from api.app.adapters import database, storage
    from api.app.adapters.ms365 import mail
    
    database.get_webhook_event = AsyncMock(return_value=mock_event)
    storage.create_workspace_folder = AsyncMock(return_value="/workspace/Quote_John_Doe")
    storage.write_json = AsyncMock()
    mail.download_attachments = AsyncMock(return_value=[
        {"name": "image.jpg", "content": b"fake_image_data"}
    ])
    storage.save_attachment = AsyncMock()
    
    # Run process
    result = await quote_processing.handle_quote_request("event-123")
    
    # Assertions
    assert result["folder_path"] == "/workspace/Quote_John_Doe"
    assert "message.json" in result["files_created"]
    assert "attachments/image.jpg" in result["files_created"]
    
    # Verify adapter calls
    database.get_webhook_event.assert_called_once_with("event-123")
    mail.download_attachments.assert_called_once()


@pytest.mark.asyncio
async def test_handle_quote_request_google():
    """Same test, but with Google provider"""
    
    # Change provider to googlews
    mock_event = {
        "id": "event-123",
        "credential_id": "cred-456",
        "provider": "googlews",  # ONLY DIFFERENCE!
        "normalized_payload": {
            "message": {
                "id": "msg-789",
                "subject": "Quote Request",
                "from": {"name": "Jane Doe", "email": "jane@example.com"},
                "has_attachments": True
            }
        }
    }
    
    # Mock googlews adapter instead
    from api.app.adapters.googlews import mail as google_mail
    google_mail.download_attachments = AsyncMock(return_value=[
        {"name": "doc.pdf", "content": b"fake_pdf_data"}
    ])
    
    # Same process, different adapter!
    result = await quote_processing.handle_quote_request("event-123")
    
    # Same assertions
    assert "attachments/doc.pdf" in result["files_created"]
```

---

## Comparison: Python vs Other Languages

### **Java (Interfaces + DI Framework)**
```java
// Explicit interface
public interface MailAdapter {
    Message getMessage(String credId, String msgId);
}

// Implementation
public class MS365MailAdapter implements MailAdapter {
    @Override
    public Message getMessage(String credId, String msgId) {
        // Implementation
    }
}

// Process with DI
@Autowired
private MailAdapter mailAdapter;

public void handleQuote(String eventId) {
    Message msg = mailAdapter.getMessage(credId, msgId);
}
```

**Python equivalent**: Use Protocol (optional) or duck typing

### **TypeScript (Interfaces)**
```typescript
// Interface
interface MailAdapter {
  getMessage(credId: string, msgId: string): Promise<Message>;
}

// Implementation
class MS365MailAdapter implements MailAdapter {
  async getMessage(credId: string, msgId: string): Promise<Message> {
    // Implementation
  }
}

// Process
async function handleQuote(eventId: string, mailAdapter: MailAdapter) {
  const msg = await mailAdapter.getMessage(credId, msgId);
}
```

**Python equivalent**: Protocol + type hints

### **C# (Interfaces + DI)**
```csharp
// Interface
public interface IMailAdapter {
    Task<Message> GetMessage(string credId, string msgId);
}

// Process with DI
public class QuoteProcessor {
    private readonly IMailAdapter _mailAdapter;
    
    public QuoteProcessor(IMailAdapter mailAdapter) {
        _mailAdapter = mailAdapter;
    }
    
    public async Task HandleQuote(string eventId) {
        var msg = await _mailAdapter.GetMessage(credId, msgId);
    }
}
```

**Python equivalent**: Constructor injection or function parameter

---

## Summary: How Flovify Achieves Platform Agnosticism

1. **Same Interface**: All provider adapters implement same methods with same signatures
   ```python
   ms365.mail.get_message(cred_id, msg_id)  # Returns normalized dict
   googlews.mail.get_message(cred_id, msg_id)  # Returns same format
   ```

2. **Provider Selection**: Process determines provider from event data, imports correct adapter
   ```python
   if provider == 'ms365':
       from adapters.ms365 import mail
   elif provider == 'googlews':
       from adapters.googlews import mail
   ```

3. **Normalized Data**: All adapters return same data structure
   ```python
   # Both return:
   {"id": "...", "subject": "...", "from": {...}, "received_at": "..."}
   ```

4. **Type Hints (Optional)**: Protocol provides IDE support without enforcement
   ```python
   from adapters.protocols import MailAdapter
   
   async def process(mail_adapter: MailAdapter):  # IDE knows methods
       await mail_adapter.get_message(...)
   ```

5. **Duck Typing**: Python doesn't care about types, just that methods exist
   ```python
   # Works with any object that has get_message() method
   await mail_adapter.get_message(...)
   ```

**Result**: ONE process that works with MS365, Google, and future providers!

---

**For Flovify, we recommend: Duck Typing + Optional Protocol Type Hints**
- Simple, Pythonic
- Type hints for IDE support
- No inheritance required
- Easy to add new providers
