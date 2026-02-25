# Skill Wiring, Stage Responsibilities

This mapping is task-13 specific and aligns role boundaries to the folder pipeline, corpus analysis, outline planning, revision loop, and batch manager flow.

## Role to Stage Map

| Role | Pipeline Stage Ownership | Stage Responsibility | Allowed MCP Tools | Forbidden Actions |
| --- | --- | --- | --- | --- |
| BatchManagerAgent | batch_manager, batch_manifest | Trigger deterministic `run-folder`, track per-doc progression, and issue controlled handoffs. | `run-folder`, `analysis-summary` | Direct stage execution (`extract`, `normalize`, `plan`, `render`, `revise`), hook-policy edits, any unapproved MCP call. |
| CorpusAgent | extract, normalize, corpus_analysis | Build deterministic corpus payloads and run `analysis-summary` for grounded planning context. | `extract`, `normalize`, `analysis-summary` | Planning/rendering/revision execution, batch-manager orchestration, hook-policy edits, unapproved MCP calls. |
| OutlineAgent | evidence_graph, deck_outline, plan | Produce evidence-grounded outline and SlideSpec artifacts from corpus analysis. | `plan` | Extraction/normalization, rendering, revision execution, hook-policy edits, broad MCP access. |
| BuildAgent | pre_render_contract_gate, render, post_render_hook_emit | Render SlideSpec and execute authoritative gate-linked hook outputs with fail-closed behavior. | `render` | Bypassing `pre_render_contract_gate` or `post_render_qa_gate`, mutating SlideSpec after validation, broad filesystem/network actions, revision execution. |
| QAAgent | post_render_qa_gate, report | Evaluate deterministic QA artifacts and publish gate outcomes via read-only summaries. | `qa-summary-read` | Modifying render outputs, re-rendering, revision calls, hook-policy edits, shell/network execution. |
| RevisionAgent | revision_loop | Execute targeted `revise` patches and rerun validation path for impacted doc scope only. | `revise` | Batch orchestration, extraction/normalization, unguided replanning, hook-gate bypass, unapproved MCP calls. |

## Skill Package Wiring

| Role | Required Skills | Why |
| --- | --- | --- |
| BatchManagerAgent | `project-planner`, `context-master` | Deterministic batch ordering, stage handoff control, and fail-closed orchestration intent. |
| CorpusAgent | `python-expert`, `context-master` | Deterministic extract/normalize transforms and grounded analysis summary generation. |
| OutlineAgent | `python-expert`, `context-master` | Evidence-graph-aware outline planning with strict contract compliance. |
| BuildAgent | `python-expert`, `debugger` | Deterministic rendering and explicit gate/hook failure handling. |
| QAAgent | `testing`, `context-master` | Contract validation, postrender gate verification, and deterministic report checks. |
| RevisionAgent | `python-expert`, `testing` | Targeted patch execution and scoped rerun validation for revise loops. |

## Command Handoff Dry-Run Contracts

| Command | Handoff Sequence | Required Gate Behavior |
| --- | --- | --- |
| `run-folder` | `BatchManagerAgent -> CorpusAgent -> OutlineAgent -> BuildAgent -> QAAgent -> RevisionAgent` | Build and QA stages must enforce `pre_render_contract_gate` and `post_render_qa_gate` without bypass paths. |
| `analysis-summary` | `BatchManagerAgent -> CorpusAgent -> BatchManagerAgent` | Summary generation is read/analyze only, no render or gate suppression side effects. |
| `revise` | `RevisionAgent -> BuildAgent -> QAAgent` | Revision can only proceed through normal pre/post gate checks and deterministic QA rerun. |

## Gate and Surface Rules

- Hook policy gates remain authoritative, `pre_render_contract_gate`, `post_render_qa_gate`, and `write_on_error_report` cannot be bypassed by any role.
- MCP surface remains allowlist-only, role assignments are explicitly limited to `extract`, `normalize`, `plan`, `render`, `qa-summary-read`, `run-folder`, `analysis-summary`, and `revise`.
- Role artifacts remain scoped to deterministic paths declared in `role_profiles.json`; no role receives wildcard filesystem permissions.
- Task 12 parser-dispatched CLI stdout side effects during MCP execution do not grant policy bypass, role allowlists still govern every operation.
