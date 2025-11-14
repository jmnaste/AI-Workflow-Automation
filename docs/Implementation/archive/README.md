# Implementation Archive

**Purpose**: Historical documentation of the tenant → credentials migration process.

---

## Context

Between November 12-14, 2025, we migrated from a "tenant-based" model to a "credentials-based" model for OAuth integrations. These documents capture that transition process and architectural decisions.

---

## Why These Documents Are Archived

These documents contain **obsolete terminology and table names** that no longer reflect the current system:

### Obsolete Terminology
- ❌ `auth.tenants` table → ✅ Now: `auth.credentials`
- ❌ `auth.tenant_tokens` table → ✅ Now: `auth.credential_tokens`
- ❌ `tenant_id` foreign key → ✅ Now: `credential_id`
- ❌ "Tenant" concept → ✅ Now: "Credential" concept

### Why We Changed

**Original Model (Incorrect)**:
- "Tenant" = one connected MS365 account
- OAuth app config (client_id, client_secret) hardcoded in environment variables
- Each tenant represented one authorized user

**Current Model (Correct)**:
- "Credential" = OAuth app configuration (reusable, admin-entered)
- Multiple credentials per provider supported (testing, production, different tenants)
- After OAuth, credential becomes "connected" to specific email account
- Follows n8n's credential pattern

---

## Archived Documents

### 1. `ms365_credentials_model.md`
**Date**: November 12, 2025  
**Purpose**: Architectural analysis comparing "tenant" vs "credentials" terminology  
**Status**: Historical - Shows reasoning for migration  
**Current Reference**: See `api/api_design.md` Section 1 for current model

**Key Content**:
- Comparison of incorrect tenant model vs correct credentials model
- n8n credential pattern analysis
- Azure App Registration terminology clarification
- Database schema migration strategy

**Why Archived**: Contains old table names and outdated concepts. The analysis was valuable for planning but implementation has since been completed differently.

---

### 2. `ms365_credentials_implementation.md`
**Date**: November 12, 2025  
**Purpose**: Step-by-step implementation plan for tenant-based model  
**Status**: Superseded - Implementation evolved during execution  
**Current Reference**: See `api_ms365_implementation_plan.md` for current implementation approach

**Key Content**:
- Phase 1: Database migration (old: 0006_tenant_tokens.sql)
- Phase 2: Auth service OAuth endpoints
- Phase 3: WebUI integration
- Testing procedures for tenant-based flow

**Why Archived**: 
- References `auth.tenant_tokens` table (now: `auth.credential_tokens`)
- Implementation plan was partially followed, then revised
- Actual migrations applied: 0007-0011 (different from this plan)

---

### 3. `credentials_refactor_plan.md`
**Date**: November 12, 2025  
**Purpose**: Planning document for tenant → credentials migration  
**Status**: Completed - Migration done, plan no longer needed  
**Current Reference**: See migration files 0007-0011 in `auth/migrations/`

**Key Content**:
- Decision summary (use "credentials" terminology)
- Drop old tables strategy
- Create new credentials tables
- Frontend refactoring plan

**Why Archived**: 
- Migration completed successfully
- Actual implementation differs slightly from plan
- Historical value only (shows decision-making process)

---

## Current Documentation (Active)

For **current system architecture**, refer to:

1. **`api/api_design.md`** - Comprehensive API architecture
   - Section 1: Credentials Model (current implementation)
   - Section 6: Database schemas (auth.credentials, auth.credential_tokens)
   - Section 4: Service layers with msgraph-sdk-python

2. **`.github/copilot-instructions.md`** - System overview
   - Credentials model explanation
   - OAuth flow documentation
   - Service boundaries

3. **`auth/README.md`** - Auth service documentation
   - OAuth & Credential Management section
   - API endpoint references

4. **`api_ms365_implementation_plan.md`** - Current implementation roadmap
   - Active development plan for API service
   - Webhook processing architecture
   - Worker implementation strategy

---

## Migration Timeline

- **Nov 12, 2025**: Identified terminology mismatch, created these planning docs
- **Nov 13, 2025**: Applied migrations 0007-0010 (drop tenants, create credentials)
- **Nov 14, 2025**: Applied migration 0011 (created_by nullable), established first OAuth connection
- **Nov 14, 2025**: Updated all active documentation to credentials model
- **Nov 14, 2025**: Archived transition documents (this archive created)

---

## Learning & Insights

### Key Lessons from Migration

1. **Terminology Matters**: "Tenant" was Microsoft-specific and confusing. "Credential" is clear and matches industry patterns (n8n, Zapier).

2. **Research Before Build**: Reviewing n8n's implementation saved us from building the wrong abstraction.

3. **Clean Breaks Are Better**: Dropping old tables completely (rather than renaming) made migration cleaner.

4. **Multiple Credentials Per Provider**: Supporting multiple OAuth apps per provider enables testing, multi-tenant deployments, and different scope configurations.

---

## If You're Reading This...

**You're probably looking for current implementation docs!**

👉 **Go to**: `api/api_design.md` for complete architecture  
👉 **Go to**: `api_ms365_implementation_plan.md` for active development plan  
👉 **Go to**: `auth/migrations/0007-0011` for applied database changes  

**Don't reference these archived docs for implementation** - they contain outdated table names and concepts that no longer exist in the system.

---

**Archive Created**: November 14, 2025  
**Archive Reason**: Terminology migration completed, documents contain obsolete references
