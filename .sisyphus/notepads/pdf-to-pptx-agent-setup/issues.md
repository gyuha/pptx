# Issues

- Initial `uv sync` failed under Python 3.14 with `pydantic-core` build error from `PyO3` max supported version 3.13.
- Resolved by constraining project Python to `<3.14` while keeping minimum `>=3.11`.
- Language diagnostics in this workspace report missing Pydantic typing stubs; runtime validation remains correct under `uv run` and explicit CLI checks.
- A first attempt to embed a base64 PNG fixture failed with `pymupdf.mupdf.FzErrorFormat`; resolved by generating the PNG fixture via PyMuPDF `Pixmap.save`.
- Language server strictness produced type-noise around dynamic parser arguments and untyped third-party PDF libs; resolved with explicit casts in CLI and typed payload dictionaries in extractor.
- `json.loads` in CLI normalize produced `reportAny` diagnostics under basedpyright; resolved by parsing through `ExtractPayload.model_validate_json` in normalize module and passing raw JSON text.
- New planner module initially failed import resolution (`ImportError: cannot import name 'NormalizedElement' from 'pptx_agent.normalize'`) because the symbol is not re-exported in `normalize.__init__`; resolved by importing from `pptx_agent.normalize.payload` directly.
- Initial task-6 error evidence command used `status` in zsh, which is read-only; switched to `exit_code` to capture expected non-zero render result.
- A first pyright pragma attempt used unsupported rule name `reportAny`; resolved by removing that pragma and keeping supported suppressions consistent with existing project files.
- Hook policy module initially triggered basedpyright diagnostics (`reportDeprecated` for `typing.Mapping` and `reportExplicitAny` in validation formatting); resolved by using `collections.abc.Mapping` and typed `cast` paths with no `Any`.
- MCP task implementation initially used `pydantic.TypeAdapter` in hook summary reader, but workspace diagnostics flagged symbol/stub issues; resolved by switching to explicit typed field validation in `read_qa_summary_file`.
- Task 9 policy rejection evidence command intentionally exits non-zero for unauthorized role action checks; the shell wrapper must tolerate this expected failure to persist `.sisyphus/evidence/task-9-agents-error.txt`.
- Task 10 required preserving deterministic run_id while avoiding stale artifacts across reruns; resolved by clearing known run outputs at run start (`output.pptx`, QA/hook sidecars, manifest) inside the selected `artifacts/<run_id>/` directory.
