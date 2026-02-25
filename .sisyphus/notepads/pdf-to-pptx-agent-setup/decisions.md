# Decisions

- Kept canonical package root as `pptx_agent` with bootstrap entrypoint `uv run python -m pptx_agent.cli`.
- Pinned required libraries in `pyproject.toml` (`PyMuPDF`, `pdfplumber`, `pypdf`, `python-pptx`, `pydantic`) for deterministic setup.
- Added `.gitignore` baseline for `.venv/`, `artifacts/`, and Python cache directories as part of task-1 scaffold.
- Chose SlideSpec schema version token `slidespec.v1` as a mandatory literal gate in the contract to prevent IR drift.
- Added `validate-ir --in <file>` as the canonical contract gate command so downstream stages can hard-fail before planning/render.
- Added CLI command `extract --in <pdf> --out <json>` with deterministic JSON serialization (`sort_keys=True`, stable block IDs) and explicit unsupported exit path (`2`).
- Chose `extract.v1` as extraction payload schema token and kept payload contract machine-friendly for downstream normalization (`status`, `reason_code`, `pages`, `blocks`, confidence metadata).
- Bounded fallback policy: run pdfplumber only for pages where PyMuPDF yields zero text blocks; do not add OCR in MVP.
- Added normalization schema token `normalize.v1` and CLI entrypoint `normalize --in <extract.json> --out <normalized.json>` as the contract bridge from `extract.v1` to planner-ready input.
- Deterministic identity policy: `deck_id` and `element_id` are derived from stable SHA256 hashes of extraction source fields rather than runtime counters.
- Normalize output now carries a machine-readable unsupported matrix (`unsupported_report.counts_by_reason` and `unsupported_report.items`) instead of free-text-only reporting.
- Added planner module (`pptx_agent.plan`) and CLI command `plan --in <normalized.json> --out <slidespec.json>` as the contract bridge from `normalize.v1` to strict `slidespec.v1`.
- Chose low-confidence marker policy for task-5: preserve raw confidence field and inject explicit `[LOW_CONFIDENCE] (confidence=...)` prefix in planned element text when confidence `< 0.75`.
- Added renderer module (`pptx_agent.render`) and CLI command `render --in <slidespec.json> --out <output.pptx>` to map `slidespec.v1` into deterministic PPTX output via python-pptx.
- Deterministic render template policy: fixed title box, fixed content region, and deterministic vertical flow by element kind (`body`/`table`) with no randomized style/layout decisions.
- Added optional `slides[].layout_hint` in SlideSpec to support explicit renderer intent while enforcing hard-fail on unknown hints with `unsupported-layout` exit path.
- Render stage writes machine-readable QA report adjacent to output (`.pptx.qa.json`) with deterministic minimum metrics (`slide_count_expected`, `slide_count_rendered`, `critical_overflow_count`).
- Added `pptx_agent.hooks` policy layer and integrated it into `render` so pre-render contract gate runs before render, post-render QA gate writes deterministic hook summary artifacts, and on-error hook writes deterministic phase/reason reports.
- Chosen deterministic run-id strategy for hook artifacts: first 16 chars of SHA256 over `{input_path.resolve()}::{output_path.resolve()}`.
- Added new module root `pptx_agent/mcp/` with a minimal stdio MCP server exposing only approved tools: `extract`, `normalize`, `plan`, `render`, and `qa-summary-read`.
- MCP tool calls are strictly schema-validated and return deterministic JSON-RPC error codes (`-32602` invalid params, `-32601` non-approved operation) with explicit machine-readable payloads.
- Added task-9 role policy config at `pptx_agent/agents/role_profiles.json` with strict stage scopes: `ContentAgent` (extract/normalize), `DesignAgent` (plan), `BuildAgent` (render/hooks), `QAAgent` (validate/report).
- Added task-9 orchestration dry-run config at `pptx_agent/agents/orchestration_dry_run.json` with ordered role handoffs and stage payload schema expectations.
- Added skill wiring documentation at `pptx_agent/agents/skill_wiring.md` mapping role-to-stage responsibilities and explicit allowed/disallowed operations.
- Added canonical integration command `uv run python -m pptx_agent.cli run-local --in <pdf> --artifacts-root artifacts` to execute extract -> normalize -> plan -> validate-ir -> preflight qa -> render -> postrender qa under one deterministic `artifacts/<run_id>/` directory.
- Added dedicated `qa` CLI gate command that writes machine-readable `pipeline.qa.gate.v1` reports and fails non-zero on critical overflow, hook-summary mismatch, provenance coverage gaps, or injection-like text markers.
- F4 scope-fidelity audit (deep) verdict: PASS. Implementation matches local MVP plan boundaries (contract-first SlideSpec pipeline, deterministic artifacts, typed minimal MCP, strict hook gates) with no verified scope creep and no missing must-have deliverables.
- F4 guardrail confirmations: no CI/workflow files present (`.github/**/*` absent), MCP surface remains restricted to approved tools only (`extract`, `normalize`, `plan`, `render`, `qa-summary-read`), and extraction explicitly keeps OCR disabled (`OCR is disabled` unsupported path).

- 2026-02-24 F1 compliance audit: Tasks 1-9 pass against acceptance criteria and listed QA evidence; Task 10 fails due missing explicit happy-path evidence for complete run_id artifact set and QA pass metrics/provenance coverage in `.sisyphus/evidence/task-10-e2e.txt`.
- Final gate set to REJECT pending Task 10 evidence completion for criteria: complete artifact set under one run_id and QA summary pass with provenance coverage metrics.

- 2026-02-24 F1 re-audit after Task 10 remediation: prior blockers resolved. `artifacts/b611d124a215514e/run_manifest.json` now records full run artifact set under one run_id; `artifacts/b611d124a215514e/qa.postrender.json` shows status=pass with zero critical overflow and provenance coverage metrics.
- Task 10 failure-path evidence remains compliant via `.sisyphus/evidence/task-10-e2e-error.txt` plus `artifacts/task10-postrender-fail/{qa.postrender.json,run_manifest.json}` confirming safe non-zero failure with deterministic artifact emission.
- Updated F1 gate: APPROVE.
