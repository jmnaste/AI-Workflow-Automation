# Architecture Documentation Index

**Date**: 2025-11-15  
**Status**: Complete - Ready for Implementation

---

## Overview

This directory contains the complete architectural documentation for Flovify's **Process + Adapters** layered architecture.

---

## Documents

### **1. Architecture Decision** (`architecture_decision.md`)
**Purpose**: Comprehensive architecture overview  
**Audience**: All team members, stakeholders

**Contents**:
- Executive summary
- Complete architecture diagram
- Layer definitions (Process vs Adapters)
- Terminology (Adapter, Service, Primitive, Process)
- File organization
- Benefits and design principles
- Implementation status

**Start here** if you're new to the architecture.

---

### **2. Refactoring Plan** (`refactor_plan.md`)
**Purpose**: Step-by-step implementation guide  
**Audience**: Developers implementing the refactor

**Contents**:
- 5-phase implementation plan (13-18 hours)
- Detailed steps for each phase
- Code examples and file structures
- Testing strategy
- Rollout options (incremental recommended)
- Success criteria

**Use this** to execute the refactoring work.

---

### **3. Platform-Agnostic Processes** (`platform_agnostic_processes.md`)
**Purpose**: Technical guide to Python abstraction patterns  
**Audience**: Developers (including Python beginners)

**Contents**:
- Dependency Injection (DI) explained
- Python patterns: Duck Typing, Protocol, ABC, Factory
- Recommended approach for Flovify
- Complete code examples
- Testing platform-agnostic code
- Comparison with other languages (Java, TypeScript, C#)

**Use this** to understand HOW processes work with multiple providers.

---

### **4. Layered Architecture** (`layered_architecture.md`)
**Purpose**: Quick reference and n8n integration guide  
**Audience**: n8n workflow developers, business users

**Contents**:
- n8n integration patterns
- Example workflows
- API endpoint catalog
- Business use cases

**Use this** when building n8n workflows.

---

## Quick Navigation

### **I want to...**

**Understand the architecture**  
→ Read `architecture_decision.md`

**Implement the refactor**  
→ Follow `refactor_plan.md`

**Learn Python abstraction patterns**  
→ Study `platform_agnostic_processes.md`

**Build n8n workflows**  
→ Reference `layered_architecture.md`

**Add a new adapter (e.g., Salesforce)**  
→ See Phase 5 in `refactor_plan.md`, copy GoogleWS pattern

**Add a new process (e.g., invoice processing)**  
→ See Phase 2 in `refactor_plan.md`, copy quote_processing.py pattern

---

## Architecture At-a-Glance

```
┌──────────────────────────────────────────────────────────┐
│  n8n Workflows (Business Users)                          │
│  → Trigger → Analyze → Route → Process                   │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP API
                     ▼
┌──────────────────────────────────────────────────────────┐
│  PROCESS LAYER (Business Logic)                          │
│  → email_classification.py                               │
│  → quote_processing.py                                   │
│  → workspace_management.py                               │
│                                                           │
│  "What to do" - Provider-agnostic                        │
└────────────────────┬─────────────────────────────────────┘
                     │ Uses
                     ▼
┌──────────────────────────────────────────────────────────┐
│  ADAPTERS LAYER (Technical Integration)                  │
│  → ms365/ (mail, drive, calendar)                        │
│  → googlews/ (mail, drive, calendar)                     │
│  → database.py, storage.py                               │
│                                                           │
│  "How to do it" - Provider-specific                      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  EXTERNAL SYSTEMS                                         │
│  → Microsoft 365, Google Workspace, PostgreSQL, Storage  │
└──────────────────────────────────────────────────────────┘
```

---

## Key Terminology

| Term | Definition | Example |
|------|------------|---------|
| **Adapter** | Integration with external system | `ms365`, `googlews`, `database` |
| **Service** | Capability within adapter | `mail`, `drive`, `calendar` |
| **Primitive** | Atomic operation | `get_message()`, `create_folder()` |
| **Process** | Business workflow | `quote_processing`, `email_classification` |

---

## Implementation Phases

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 0 | Test current code | 30-60 min | ⏳ In Progress |
| 1 | Create adapter structure | 2-3 hours | ⏳ Planned |
| 2 | Create process layer | 3-4 hours | ⏳ Planned |
| 3 | Add process endpoints | 1-2 hours | ⏳ Planned |
| 4 | Add MS365 primitives | 2-3 hours | ⏳ Planned |
| 5 | Implement GoogleWS | 4-5 hours | ⏳ Planned |

**Total**: 13-18 hours

---

## File Structure

```
api/app/
├── processes/              # Business workflows
│   ├── email_classification.py
│   ├── quote_processing.py
│   └── workspace_management.py
│
├── adapters/               # External integrations
│   ├── ms365/
│   │   ├── mail.py
│   │   ├── drive.py
│   │   └── _auth.py
│   ├── googlews/
│   │   ├── mail.py
│   │   ├── drive.py
│   │   └── _auth.py
│   ├── database.py
│   └── storage.py
│
└── routes/                 # API endpoints
    ├── processes.py        # n8n endpoints
    └── ms365.py           # Webhooks
```

---

## API Endpoints

### **Process Endpoints** (for n8n)
```
POST /api/processes/email/analyze       # Classify email
POST /api/processes/quote/handle        # Process quote
POST /api/processes/workspace/create    # Create workspace
GET  /api/processes/events/pending      # Poll events
```

### **Adapter Endpoints** (webhooks)
```
POST /api/ms365/webhook                 # MS365 notifications
POST /api/googlews/webhook              # Google notifications
POST /api/ms365/subscriptions           # Manage subscriptions
```

---

## Example: Quote Request Workflow

**n8n Workflow**:
```
1. Poll for new events
   GET /api/processes/events/pending

2. Analyze email
   POST /api/processes/email/analyze
   → {intent: "quote_request", confidence: 0.95}

3. Route by intent (Switch node)

4. Process quote request
   POST /api/processes/quote/handle
   → Creates folder with message.json, attachments/
```

**Result**:
```
/workspace/Quote_JohnDoe_2025-11-15/
├── message.json        # Full email content
├── metadata.json       # AI analysis
└── attachments/
    ├── image1.jpg
    └── image2.jpg
```

---

## Design Principles

### **Process Layer**
✅ Business language (`handle_quote_request`)  
✅ Provider-agnostic (works with MS365 or Google)  
✅ Orchestrates adapters  
❌ Never imports provider libraries directly  

### **Adapters Layer**
✅ Provider-specific implementation  
✅ Atomic operations (`get_message`, `create_folder`)  
✅ Normalized output (same format across providers)  
✅ Handles auth, retries, errors  

---

## Benefits

1. **Platform Agnostic**: Switch MS365 → Google by changing adapter only
2. **Testable**: Mock adapters, test processes in isolation
3. **Maintainable**: Clear boundaries, single responsibility
4. **Extensible**: Add Salesforce, Slack adapters easily
5. **n8n Ready**: Simple, high-level APIs for workflows

---

## Getting Started

### **For Developers**
1. Read `architecture_decision.md` (15 min)
2. Review `refactor_plan.md` Phase 1 (10 min)
3. Study `platform_agnostic_processes.md` examples (20 min)
4. Start implementing Phase 1

### **For n8n Workflow Builders**
1. Review `layered_architecture.md` (10 min)
2. Look at example workflows
3. Start building with `/api/processes/*` endpoints

### **For Python Beginners**
1. Read `platform_agnostic_processes.md` from top to bottom
2. Focus on "Duck Typing" pattern
3. Study complete examples
4. Try mocking adapters in tests

---

## Questions & Support

**Architecture questions**: Reference `architecture_decision.md`  
**Implementation questions**: Check `refactor_plan.md`  
**Python patterns**: See `platform_agnostic_processes.md`  
**n8n integration**: Use `layered_architecture.md`

---

## Related Documents

- `docs/Implementation/api_ms365_implementation_plan.md` - MS365 webhook implementation
- `docs/Implementation/process_adapters_refactoring.md` - Detailed refactoring steps (superseded by `refactor_plan.md`)
- `.github/copilot-instructions.md` - AI assistant instructions (includes architecture)

---

**Architecture Status**: ✅ Documented, ready for implementation  
**Next Step**: Complete Phase 0 (test current code), then begin Phase 1 (create adapter structure)
