# Learnings

- Task 1 bootstrap works cleanly with `uv` when `requires-python` is constrained to `>=3.11,<3.14` in `pyproject.toml` on this machine.
- Core dependency smoke command for the required PDF/PPTX stack is reliable: `uv run python -c "import fitz, pdfplumber, pypdf, pptx, pydantic; print('ok')"`.
- A minimal CLI smoke entrypoint can stay zero-side-effect by just parsing args and returning `0` in `pptx_agent.cli:main`.
- A strict SlideSpec v1 contract can be kept compact with nested Pydantic models while still enforcing provenance (`source_page`, `evidence`, `confidence`) on each slide element.
- CLI validation UX is clear when flattening Pydantic error locations into dot-paths (for example: `slides.0.elements.0.source_page`).
- Task 3 extraction works with a deterministic `extract.v1` JSON payload containing `pages[].blocks[]` and per-block `confidence` + `confidence_meta`.
- Using PyMuPDF `get_text("blocks", sort=True)` as primary extraction plus selective pdfplumber fallback only on empty-text pages keeps fallback bounded and predictable.
- Unsupported scanned/image-only PDFs can be handled safely by returning an explicit `unsupported` status and reason code (`scanned_or_image_only`) while still writing machine-readable output JSON.
- Normalization can stay deterministic by hashing stable source facts (`input.file`, `page_number`, `block_id`, `kind`, `text`, `bbox`) for `element_id` generation.
- Provenance coverage is straightforward to enforce at normalize time by requiring `source_page`, `source_block_id`, `evidence`, and `confidence` on every normalized element model.
- Reporting unsupported inputs in a structured report (`counts_by_reason` + per-item detail records) works well for both unsupported documents and unsupported block kinds.
- Planning stage can stay deterministic by mapping one normalized page to one slide (`slide_pNNN`) and using first text block as title intent, then body/table intents for remaining elements.
- Low-confidence signaling can be kept SlideSpec-compatible without schema changes by prefixing element text with explicit `[LOW_CONFIDENCE] (confidence=...)` while preserving the original numeric confidence value.
- Renderer determinism is stable when using fixed canvas geometry (10x7.5 in), fixed title/content boxes, and element-kind-driven vertical flow weights rather than adaptive layout heuristics.
- A machine-readable render QA artifact can be generated deterministically per run (`<output>.pptx.qa.json`) with stable fields (`slide_count_expected`, `slide_count_rendered`, `critical_overflow_count`) and a documented placeholder overflow metric policy.
- Explicit unsupported-layout handling is reliable by allowing optional `layout_hint` in SlideSpec and hard-failing render with `unsupported-layout` when the hint is not in the renderer's supported set.
- Task 7 hook policy layer works cleanly when pre-render validation wraps contract failures into explicit hook policy errors and keeps the render command exit semantics deterministic.
- Writing hook artifacts adjacent to output (`.hooks.qa.json`, `.hooks.error.json`) provides deterministic, machine-readable policy evidence without changing the existing `.qa.json` report contract.
- Task 8 MCP surface can stay minimal and deterministic by implementing only `initialize`, `tools/list`, and `tools/call` over stdio JSON-RPC with no unrestricted shell/filesystem/network tools.
- Typed MCP tool schemas from Pydantic `model_json_schema()` provide machine-readable argument contracts while preserving existing pipeline function reuse (`extract` -> `normalize` -> `plan` -> `render` + `qa-summary-read`).
- Task 9 role configs are easiest to keep auditable as JSON with explicit `allowed_tools`, `forbidden_actions`, and handoff chain metadata per role.
- A dry-run orchestration config can validate stage handoffs without executing pipeline work by checking stage operations against each role's allowed MCP surface.
- End-to-end local runs are easiest to keep auditable with a run manifest (`run_manifest.json`) plus preflight/postrender QA gate artifacts (`qa.preflight.json`, `qa.postrender.json`) colocated in `artifacts/<run_id>/`.
- Injection-like text can be blocked safely before render by scanning planned slide titles/body/evidence for high-risk markers and failing QA preflight with non-zero exit while leaving `output.pptx` absent.
- F3 manual QA confirms README canonical command `uv run python -m pptx_agent.cli run-local --in fixtures/extract/born_digital_sample.pdf --artifacts-root artifacts` exits `0`, produces `run_id=b611d124a215514e`, and writes pass artifacts under `artifacts/b611d124a215514e/`.
- Deterministic run_id behavior is verified by path-hash expectation: fixture absolute-path SHA-256 prefix resolves to `b611d124a215514e`, matching runtime output and `run_manifest.json`.
- Failure safety is intact for malformed SlideSpec: `uv run python -m pptx_agent.cli validate-ir --in fixtures/slidespec_missing_source_page.json` exits `1` with explicit missing provenance field (`slides.0.elements.0.source_page`).
- Injection-like QA gate fails safely: `uv run python -m pptx_agent.cli qa --slidespec artifacts/task-f3-unsafe/unsafe_slidespec.json --out artifacts/task-f3-unsafe/qa.injection.json --run-id task-f3-unsafe` exits `1` and records `unsafe_text_absent=false` with marker `ignore previous instructions`.

-  post-render hook failures must not short-circuit artifact emission; persist  and  (with  + ) before returning non-zero.

- run-local post-render hook failures must not short-circuit artifact emission; persist qa.postrender.json and run_manifest.json (with status=failed_postrender + failures) before returning non-zero.
