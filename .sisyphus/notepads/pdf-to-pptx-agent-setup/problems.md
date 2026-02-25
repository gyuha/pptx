# Problems

## 2026-02-24 F2 quality gate findings

- [critical] `run-local` drops required postrender artifacts on hook-gate failure: when `post_render_qa_gate` raises, `_cmd_run_local` returns before writing `qa.postrender.json` and `run_manifest.json` (`pptx_agent/cli.py:550`, `pptx_agent/cli.py:574`, `pptx_agent/cli.py:611`). Repro: generated long-text PDF via `uv run python` and observed failure run directory missing both files.
- [major] Planner does not fail closed on unsupported normalized input: `plan_normalized_model` always emits SlideSpec (including synthetic empty slide) even if `normalized.status == "unsupported"` (`pptx_agent/plan/payload.py:76`, `pptx_agent/plan/payload.py:79`). Repro: `uv run python -m pptx_agent.cli plan` on unsupported `normalize.v1` payload exited `0` and produced `slidespec.json`.
- [major] Determinism/provenance drift from path-string hashing: `deck_id` and `element_id` hash `extract_payload.input.file` raw string rather than canonicalized path/content (`pptx_agent/normalize/payload.py:114`, `pptx_agent/normalize/payload.py:137`). Same file invoked as `a.pdf` vs `./a.pdf` yields different IDs.
- [major] Run-id semantics are inconsistent across pipeline artifacts: artifact run uses `_deterministic_run_id(input_path)` (`pptx_agent/cli.py:452`), hook artifacts use `compute_run_id(slidespec, output)` (`pptx_agent/cli.py:549`, `pptx_agent/hooks/policy.py:69`), QA command defaults to `_deterministic_run_id(slidespec_path)` (`pptx_agent/cli.py:429`). This weakens cross-artifact correlation and failure forensics.
- [major] MCP render tool can write to arbitrary filesystem paths (`output_pptx` unbounded) with no sandbox/root policy check (`pptx_agent/mcp/server.py:56`, `pptx_agent/mcp/server.py:199`). This is a safety risk if MCP caller surface is exposed beyond trusted local use.

## 2026-02-24 F2 rerun after run-local remediation

- Prior critical defect is resolved: post-render-fail runs now persist `qa.postrender.json` + `run_manifest.json` before non-zero exit (`pptx_agent/cli.py:620`, `pptx_agent/cli.py:626`, `pptx_agent/cli.py:647`). Evidence: `artifacts/task10-postrender-fail/run_manifest.json`, `artifacts/task10-postrender-fail/qa.postrender.json`, and repro command `uv run python - <<'PY' ... run-local ... PY` returned `exit_code 1` with both files present.
- Remaining blocker: planner still accepts unsupported normalized payload and emits SlideSpec with exit `0` (`pptx_agent/plan/payload.py:76`, `pptx_agent/plan/payload.py:79`, `pptx_agent/cli.py:334`). Repro: `uv run python - <<'PY' ... pptx_agent.cli plan --in normalized.json --out slidespec.json ... PY` -> `exit_code 0`, `slidespec_exists True`.
- Non-blocking major debt: path-string hashing drift persists (`pptx_agent/normalize/payload.py:114`, `pptx_agent/normalize/payload.py:137`) and run-id semantics remain split (`pptx_agent/cli.py:452`, `pptx_agent/cli.py:549`, `artifacts/task10-postrender-fail/run_manifest.json:17`). MCP output path is still unrestricted (`pptx_agent/mcp/server.py:199`).

## 2026-02-24 F2 blocker closure follow-up

- Planner now fails closed for unsupported normalized payloads: `plan` exits non-zero and prints explicit reason (`Unsupported planning input: normalized.status must be 'ok' (got 'unsupported').`) with no unsupported SlideSpec output emitted. Repro evidence: `artifacts/task-5-plan-failclosed/plan.unsupported.out`, `.sisyphus/evidence/task-5-plan-error-addendum.jsonl`.

## 2026-02-24 F2 final verdict

- Previous planner blocker is resolved in code and behavior: fail-closed guard + CLI ValueError handling are active (`pptx_agent/plan/payload.py:77`, `pptx_agent/cli.py:306`) and repro now returns `exit_code 1` with `slidespec_exists False`.
- Remaining findings are non-blocking debt for trusted local MVP scope: path-string hash drift (`pptx_agent/normalize/payload.py:114`, `pptx_agent/normalize/payload.py:125`) and unrestricted MCP `output_pptx` sink (`pptx_agent/mcp/server.py:199`).
- Final F2 gate verdict: APPROVE for current plan scope.
