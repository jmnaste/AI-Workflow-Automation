# Decision Guide — No‑Code vs Hybrid (AI + Code)

Goal: Choose the simplest path that still meets business‑grade requirements. Use no‑code where it fits; switch to hybrid when reliability, safety, or scale is at stake.

---

## Use no‑code when (good fit)
- Stateless or low‑risk tasks
- Human‑readable automations (notifications, routing, simple transforms)
- No PII/regulated data; light permissions
- Low to moderate volume; latency not critical
- Minimal AI decisioning (or none)

### Examples (easy with no‑code)
- Notifications and escalations (email/Slack/Teams)
- Form → CRM or spreadsheet; lead capture/assignment
- Calendar/scheduling workflows
- File sync/rename; S3/Drive/SharePoint moves
- Social posting; RSS → newsletter draft
- Basic data sync between SaaS tools
- Simple webhook passthroughs

### Anti‑patterns (when simple becomes complex)
- Off the tool’s happy path: nonstandard validations, partial failure handling, idempotency requirements
- Heavy branching with state: multi‑step conditions across time or retries
- Versioning and rollback needs: multiple variants of prompts, tools, or flows
- Hidden custom code: scattered scripts and webhooks that are hard to test and govern
- Cross‑tenant or RBAC rules that don’t map cleanly to the tool’s model

---

## Use hybrid when (required for business‑grade)
- Multi‑step AI decisions with evaluation and versioning
- PII/regulated data requiring redaction, audit, and RBAC
- SLAs/SLOs on latency, success rates, or throughput
- Idempotency, retries, rollbacks, and compensations
- HITL approvals with lineage and annotations
- Multi‑tenant isolation; quotas; cost/resource controls
- Batch/backfill jobs with throttling and lineage

### Examples (need hybrid)
- Document extraction with validation → ERP write (invoice, PO, contract)
- Support triage with macro suggestions + HITL + audit trail
- Onboarding/KYC: ID validation with PII redaction and event lineage
- RAG with grounded answers, eval harness, and versioned prompts/models
- Lead routing with enrichment, scoring, and policy checks
- Cash application: remittance matching, exception handling, rollback
- Procurement: 3‑way match (PO, receipt, invoice) with reconciliation
- Risk triage: rule‑based + model‑based scoring with overrides and appeals

---

## Quick rubric (checklist)
- Does it touch PII or regulated data? → Hybrid
- Do we promise latency/reliability (SLO/SLA)? → Hybrid
- Are decisions evaluated/versioned over time? → Hybrid
- Do we need retries/rollbacks or batch replays? → Hybrid
- Otherwise, can no‑code deliver 80% quickly? → Start no‑code; add code later if needed

---

## Architecture boundaries
- No‑code: triggers, OAuth, schedules, simple transforms, human notifications
- Code: typed APIs (FastAPI), cognition/state machines (LangGraph), validations/evals
- Shared: Workflow Run Management (runs, state timelines, diagnostics) for evidence and control

---

## Evidence & metrics to track
-- Time‑to‑feature (time to benefit)
-- First‑pass success (and quality measures)
-- AI contribution stability & reliability (consistency across runs; drift; HITL escalation rate)
-- Supporting diagnostics: p95 run duration; resource usage/run
-- Staff pressure relief (utilization/queue depth)
-- Customer experience trend (if available)

---

References
- WRM Executive Summary: docs/workflow_run_management_summary.md
- Full WRM Spec: docs/workflow_run_management_spec.md
