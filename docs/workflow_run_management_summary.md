# Workflow Run Management — Executive Summary (Outcome‑First)

Primary objective: Deliver automated workflows that achieve the required outcomes reliably. Workflow Run Management (WRM) is the evidence layer that keeps outcomes visible and controllable while you iterate.

---

## Why it matters (business view)
- Show, don’t tell: every run is visible with clear states, timings, and decisions.
- Faster learning loops: diagnose failures and ship small improvements with confidence.
- Credible reporting: before/after indicators are tied to actual runs.

## What you see (operators & stakeholders)
- Run list with status, version, env, started/completed, duration
- State timeline with retries, failure reasons, and HITL decisions
- Steps with resource usage (tokens/compute), validation results, and last error
- Effectiveness snapshot: first‑pass success, accuracy/quality, throughput deltas

## What you can do (actions)
- Re‑run with context; cancel; annotate; tag
- Compare versions (before/after); export runs; subscribe to webhooks and alerts

## How we measure (indicators)
- Time‑to‑feature (time to benefit)
- First‑pass success and quality measures
- p95 run duration and resource usage per run
- Staff pressure relief or CX trend (when available)

## When to deploy WRM
- Business‑grade targets (SLAs, audit, HITL, or regulated data)
- Multi‑step AI decisions; retries and rollbacks matter
- You need to prove improvements with before/after evidence

## Privacy & retention (defaults)
- Field‑level redaction before persistence/LLM usage
- Role‑based access; per‑tenant policies
- Raw logs: 30–90 days; summaries/metrics: 365+ days (tunable)

## Implementation quickstart
- API: GET runs, GET run, GET steps; actions: rerun/cancel/annotate/tag
- Correlation: run.id ↔ trace_id; step.id ↔ span_id
- Webhooks: run.started/completed/failed/waiting_human/canceled; step.completed/failed

Reference
- Full spec: docs/workflow_run_management_spec.md
- Decision guide (no‑code vs hybrid): docs/decision_guide_no_code_vs_hybrid.md
