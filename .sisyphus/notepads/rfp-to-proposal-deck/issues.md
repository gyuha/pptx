# Issues

- Task 6 introduced a new required `source_span` field in evidence graph provenance; legacy evidence graph fixtures had to be updated to remain contract-valid.
- Task 7 revealed that `OutlineVisualSpec(kind="image")` fails immediately unless `image_prompt` and `image_model` are provided in the same constructor call due to after-model validation.
- Task 7 regression surfaced when planner emitted unsupported renderer hints (`image_focus`, `table_focus`), causing `run-local` to fail with `unsupported-layout` before PPTX generation.
- Task 8 image API error scenario requires explicit `PPTX_AGENT_IMAGE_API_PROVIDER=openai` with empty `OPENAI_API_KEY`; without provider override, default mock image provider masks credential failures.
- Task 9 citation completeness now depends on evidence-reference shape; legacy or ad-hoc evidence strings that omit structured citation tokens can fail QA despite non-empty provenance fields.
- Task 10 fixture drift risk: revise patches that hardcode slide IDs must match the actual planner ID format (`slide_001` with underscore in current runs), otherwise revise fails with `unknown_target` before gating.
- Task 12 note: MCP revision trigger currently reuses CLI handlers via parser-dispatched commands, so CLI stdout messages still emit during tool execution even though JSON-RPC payloads remain deterministic.
- LSP diagnostics are currently limited for these files in this workspace because `biome` is not installed for `.json` and no `.md` LSP is configured, so validation was done with deterministic JSON/policy assertions instead.
- Task 14 shell gotcha: deriving `RUN_DIR` by mixing stdin heredoc fragments can split path values; constructing `RUN_DIR` directly from `BATCH_DIR/docs/$DOC_ID` is safer for repeatable regression scripts.
