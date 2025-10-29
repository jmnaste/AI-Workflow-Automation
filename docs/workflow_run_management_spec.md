# Workflow Run Management — Product/Engineering Spec

## Purpose
Provide a workflow-first observability layer that makes every run, state transition, and diagnostic highly visible to operators and stakeholders. Telemetry (metrics/logs/traces) supports analysis and tuning; the primary surface is a clear run management UI and API.

---

## Users & Jobs-to-be-Done
- Operations/Support: Triage failed or slow runs, re-run with context, annotate outcomes.
- Engineers: Debug decisions/steps with traces, logs, and input/output samples (redacted).
- Product/Managers: Verify effectiveness and experience KPIs tied to actual runs.
- Compliance/Security: Audit who did what, when; confirm redaction and access controls.

---

## Success Criteria (acceptance)
- Find any run within 3 clicks by workflow, status, time, or tag.
- Understand what happened (and why) within 60 seconds from run detail.
- Re-run with context or mark as resolved without leaving the run view.
- Link any run to its business event and show before/after indicators.

---

## Data Model (contract)
- Run
  - id, workflow_name, workflow_version, environment (dev/stage/prod)
  - status (queued, running, completed, failed, canceled, waiting_human)
  - started_at, completed_at, duration_ms
  - actor (system|human), hitl (requested|approved|rejected|null)
  - business_event_id (external correlation), tenant_id (multi-tenant safety)
  - inputs_summary (redacted), outputs_summary (redacted)
  - effectiveness: { first_pass_success, accuracy, throughput_delta }
  - diagnostics: { trace_id, resource_usage: { tokens, compute_ms }, error_code, error_message }
  - tags: string[]; annotations: [{author, note, at}]
- Step
  - id, run_id, name, type (tool|model|decision|io)
  - status, started_at, completed_at, duration_ms, retries
  - details: { model, tool, endpoint, parameters_redacted }
  - io: { input_redacted, output_redacted }
  - diagnostics: { span_id, resource_usage: { tokens, compute_ms }, error_code, error_message }
  - validation: { passed, score?, reasons? }

---

## Example — Run JSON
```json
{
  "id": "run_01HXY...",
  "workflow_name": "invoice_extraction",
  "workflow_version": "1.8.3",
  "environment": "prod",
  "status": "completed",
  "started_at": "2025-10-28T10:14:02Z",
  "completed_at": "2025-10-28T10:14:04Z",
  "duration_ms": 2120,
  "actor": "system",
  "hitl": null,
  "business_event_id": "erp:invoice#98421",
  "tenant_id": "acme-inc",
  "inputs_summary": { "file": "invoice_98421.pdf", "pages": 2 },
  "outputs_summary": { "total": 1732.55, "currency": "USD", "line_items": 5 },
  "effectiveness": { "first_pass_success": true, "accuracy": 0.97, "throughput_delta": 2.3 },
  "diagnostics": { "trace_id": "trc-8cbd...", "resource_usage": { "tokens": 3124, "compute_ms": 480 }, "error_code": null, "error_message": null },
  "tags": ["invoice", "prod"],
  "annotations": [ { "author": "ops@acme", "note": "Valid totals.", "at": "2025-10-28T10:16:21Z" } ]
}
```

---

## Example — Step JSON
```json
{
  "id": "step_01HXY...",
  "run_id": "run_01HXY...",
  "name": "extract_fields",
  "type": "model",
  "status": "completed",
  "started_at": "2025-10-28T10:14:03Z",
  "completed_at": "2025-10-28T10:14:03.8Z",
  "duration_ms": 800,
  "retries": 0,
  "details": { "model": "gpt-4o-mini", "parameters_redacted": { "temperature": 0 } },
  "io": { "input_redacted": { "content_type": "pdf" }, "output_redacted": { "fields": ["total", "date", "vendor"] } },
  "diagnostics": { "span_id": "spn-a13d...", "resource_usage": { "tokens": 2200, "compute_ms": 380 }, "error_code": null, "error_message": null },
  "validation": { "passed": true, "score": 0.96 }
}
```

---

## UI — Run List
- Columns: Run ID, Workflow, Version, Env, Status, Started, Duration, HITL, Tags, Owner/Actor
- Filters: status, workflow, env, version, date/time range, tag, tenant, error_code, hitl state
- Bulk actions: re-run, cancel, tag, export (CSV/JSON), assign owner
- Row affordances: quick view (popover with last error and last state), copy IDs

## UI — Run Detail
- Header: core metadata, business_event_id link, CTA: Re-run, Cancel, Add tag, Annotate
- State Timeline: sequential or graph view of states with durations and retry badges
- Steps Table: step name, type, duration, retries, resource usage, validation, last error
- Diagnostics Tabs: Traces, Logs, I/O (redacted), Attachments, HITL Decisions, Annotations
- Business Panel: effectiveness snapshot (first-pass success, accuracy, throughput delta), customer experience notes if available

---

## API (FastAPI sketch)
- GET /runs?workflow&status&env&from&to&tag&page&limit
- GET /runs/{id}
- GET /runs/{id}/steps
- POST /runs/{id}/rerun { reason, note }
- POST /runs/{id}/cancel { reason }
- POST /runs/{id}/annotate { note }
- POST /runs/{id}/tags { add:[], remove:[] }
- Webhooks: run.started, run.completed, run.failed, run.waiting_human, run.canceled, step.completed, step.failed

### Query semantics
- Pagination: cursor-based, opaque next_token
- Sorting: -started_at (default), status, duration
- Filtering: multi-value (status=completed,failed), regex on tags (server-side safe)

---

## Diagnostics & Correlation
- Correlation: run.id ↔ trace_id; step.id ↔ span_id (1:1 mapping where possible)
- Structured logs: JSON with run_id, step_id, state, msg, level, ts
- Error taxonomy: transient (retryable), validation_failed, external_api, policy_denied, bug
- Attachments: link artifacts (PDF, CSV, JSON) to run with secure signed URLs

---

## Metrics & SLOs
- Run health: success_rate, first_pass_success_rate, retries_per_100, mttr (mean time to repair)
- Performance: p95_run_duration, p95_step_duration[name], resource_usage_per_run (tokens/compute)
- Experience: time_to_feature (where applicable), customer_experience_index (if captured)
- SLOs: p95_run_duration < target; success_rate ≥ target; event delivery < 5s 99%; diagnostics available for 99.9% of runs

---

## Roles & Access
- Viewer: read-only runs and steps (redacted I/O)
- Operator: all viewer + re-run, cancel, annotate, tag
- Admin: all operator + retention, PII policy, webhook keys

---

## Privacy, Redaction, Retention
- Redaction: PII removed before persistence; inline masking for I/O previews
- Field-level policies: redact, hash, tokenize; per-tenant configuration
- Retention: defaults (e.g., 30–90 days for raw logs; 365+ days for summaries/metrics)

---

## Edge Cases & Error Modes
- Partial completion (some steps succeeded): display mixed state with guided resolution
- Long-running/paused for HITL: show waiting_human with SLA clock and reminders
- Duplicates/retries: deduplicate by business_event_id; show lineage and parent/child runs
- Backfills/batch replays: tag and isolate in views; throttle to protect prod traffic
- Missing traces/logs: still render run and states; surface gaps with guidance

---

## Minimal Implementation Plan
1) Data model and endpoints (GET runs, GET run, GET steps)
2) Run list + detail UI (timeline + steps table)
3) Basic diagnostics tab: traces and logs correlation
4) Actions: annotate, tag, re-run, cancel
5) Webhooks and alert hooks for failed/waiting runs

Later: search across I/O (redacted), advanced analytics, comparison view (A/B across versions), notebook export.
