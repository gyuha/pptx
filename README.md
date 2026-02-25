# pptx

Local MVP PDF-to-PPTX pipeline with deterministic artifacts and QA gates.

## Canonical Local Runbook

Single-command canonical path:

```bash
uv run python -m pptx_agent.cli run-local --in fixtures/extract/born_digital_sample.pdf --artifacts-root artifacts
```

This command executes the full stage order using existing contracts:

1. `extract` -> `artifacts/<run_id>/extract.json`
2. `normalize` -> `artifacts/<run_id>/normalized.json`
3. `plan` -> `artifacts/<run_id>/slidespec.json`
4. `validate-ir` (pre-render contract gate)
5. `qa` preflight gate (provenance coverage + unsafe text checks)
6. `render` -> `artifacts/<run_id>/output.pptx`
7. hook QA summary + `qa` postrender gate

Deterministic artifact layout per run:

- `artifacts/<run_id>/extract.json`
- `artifacts/<run_id>/normalized.json`
- `artifacts/<run_id>/slidespec.json`
- `artifacts/<run_id>/output.pptx`
- `artifacts/<run_id>/output.pptx.qa.json`
- `artifacts/<run_id>/output.pptx.hooks.qa.json`
- `artifacts/<run_id>/output.pptx.hooks.error.json` (only on failure)
- `artifacts/<run_id>/qa.preflight.json`
- `artifacts/<run_id>/qa.postrender.json`
- `artifacts/<run_id>/run_manifest.json`

## QA Gate Command

Run QA gate directly (fails non-zero on critical issues):

```bash
uv run python -m pptx_agent.cli qa --slidespec artifacts/<run_id>/slidespec.json --qa-report artifacts/<run_id>/output.pptx.qa.json --hook-summary artifacts/<run_id>/output.pptx.hooks.qa.json --out artifacts/<run_id>/qa.postrender.json --run-id <run_id>
```

The gate enforces:

- slide/spec validity
- zero critical overflow
- rendered slide count match
- hook summary pass
- provenance coverage ratio
- injection-like marker absence in titles/body/evidence text

## Folder Orchestration

Batch run with deterministic per-document artifacts and one output deck per supported input file:

```bash
uv run python -m pptx_agent.cli run-folder --in-dir fixtures/extract --out-dir output --artifacts-root artifacts/batches --model-profile local
```

Default policy:

- `model-profile=local`
- `continue-on-error=true`
- final command exits `1` when any document fails or is unsupported

Batch artifacts are written to `artifacts/batches/<batch_id>/`:

- `batch_manifest.json`
- `docs/<doc_id>/...` (per-document `run-local` style artifacts including `run_manifest.json`, `qa.preflight.json`, `qa.postrender.json`, and `output.pptx`)

## End-to-End Fixture Set

Task 14 regression pack uses these deterministic fixtures:

- `fixtures/rfp_input/doc-a.pdf`
- `fixtures/rfp_input/doc-b.pdf`
- `fixtures/rfp_input/doc-c.docx`
- `fixtures/feedback_patch_revise_valid.json`
- `fixtures/feedback_patch_revise_invalid_unknown_slide.json`

## Operator Runbook: Folder Workflow + Revision Loop

Copy-paste sequence for a local profile happy run and targeted revise pass:

```bash
set -euo pipefail

WORK_ROOT=".sisyphus/tmp/task14/happy"
OUT_DIR="$WORK_ROOT/out"
ART_ROOT="$WORK_ROOT/artifacts"

rm -rf "$WORK_ROOT"
mkdir -p "$OUT_DIR" "$ART_ROOT"

uv run python -m pptx_agent.cli run-folder \
  --in-dir fixtures/rfp_input \
  --out-dir "$OUT_DIR" \
  --artifacts-root "$ART_ROOT" \
  --model-profile local

python - <<'PY'
import json
from pathlib import Path

art_root = Path('.sisyphus/tmp/task14/happy/artifacts')
batch_dirs = sorted(p for p in art_root.iterdir() if p.is_dir())
assert len(batch_dirs) == 1, f"expected one batch dir, got {len(batch_dirs)}"
batch_dir = batch_dirs[0]
manifest = json.loads((batch_dir / 'batch_manifest.json').read_text())
registry = json.loads((batch_dir / 'document_registry.json').read_text())
assert manifest['runtime']['model_profile'] == 'local', manifest['runtime']
assert manifest['counts']['total'] == 3, manifest['counts']
assert manifest['counts']['failed'] == 0, manifest['counts']
assert len(registry['documents']) == 3, len(registry['documents'])
out_dir = Path('.sisyphus/tmp/task14/happy/out')
assert len(list(out_dir.glob('*.pptx'))) == 3, sorted(p.name for p in out_dir.glob('*.pptx'))
print(batch_dir)
PY

DOC_ID="$(python - <<'PY'
import json
from pathlib import Path

batch_dir = sorted(Path('.sisyphus/tmp/task14/happy/artifacts').iterdir())[0]
manifest = json.loads((batch_dir / 'batch_manifest.json').read_text())
target = next(d for d in manifest['documents'] if d['input_file'].endswith('doc-a.pdf'))
print(target['doc_id'])
PY
)"

RUN_DIR="$(python - <<'PY'
from pathlib import Path
batch_dir = sorted(Path('.sisyphus/tmp/task14/happy/artifacts').iterdir())[0]
doc_id = Path('/dev/stdin').read_text().strip()
print(batch_dir / 'docs' / doc_id)
PY
<<< "$DOC_ID")"
export RUN_DIR

uv run python -m pptx_agent.cli revise \
  --run-dir "$RUN_DIR" \
  --feedback fixtures/feedback_patch_revise_valid.json

python - <<'PY'
import json
import os
from pathlib import Path

run_dir = Path(os.environ['RUN_DIR'])
manifest = json.loads((run_dir / 'run_manifest.json').read_text())
assert manifest['status'] == 'pass', manifest['status']
assert manifest['feedback_reference']['path'].endswith('fixtures/feedback_patch_revise_valid.json')
assert manifest['targeted_slide_ids'] == ['slide_001'], manifest['targeted_slide_ids']
assert (run_dir / 'qa.postrender.json').exists()
assert (run_dir / 'output.pptx').exists()
print('revise ok:', run_dir)
PY
```

Expected results:

- `run-folder` exits `0`.
- `batch_manifest.json` shows `total=3`, `failed=0`, `runtime.model_profile=local`.
- exactly three output decks exist under `.sisyphus/tmp/task14/happy/out`.
- `revise` exits `0` and updates only `targeted_slide_ids=['slide_001']`.

## Model Profile Behavior

- `--model-profile local` is the default and does not require cloud credentials.
- `--model-profile cloud` fails fast when cloud credentials are missing.
- Selected profile is persisted in per-doc `run_manifest.json` and batch `batch_manifest.json` runtime fields.

## Regression Command Pack

Happy regression pack (must exit `0`):

```bash
bash -c 'set -euo pipefail
WORK_ROOT=".sisyphus/tmp/task14/happy";
OUT_DIR="$WORK_ROOT/out";
ART_ROOT="$WORK_ROOT/artifacts";
rm -rf "$WORK_ROOT";
mkdir -p "$OUT_DIR" "$ART_ROOT";
uv run python -m pptx_agent.cli run-folder --in-dir fixtures/rfp_input --out-dir "$OUT_DIR" --artifacts-root "$ART_ROOT" --model-profile local;
python - <<"PY"
import json
from pathlib import Path
batch_dir = sorted(Path(".sisyphus/tmp/task14/happy/artifacts").iterdir())[0]
manifest = json.loads((batch_dir / "batch_manifest.json").read_text())
assert manifest["counts"]["total"] == 3
assert manifest["counts"]["failed"] == 0
assert manifest["runtime"]["model_profile"] == "local"
target = next(d for d in manifest["documents"] if d["input_file"].endswith("doc-a.pdf"))
run_dir = batch_dir / "docs" / target["doc_id"]
assert (run_dir / "qa.preflight.json").exists()
assert (run_dir / "qa.postrender.json").exists()
assert (run_dir / "run_manifest.json").exists()
assert (run_dir / "output.pptx").exists()
assert len(list(Path(".sisyphus/tmp/task14/happy/out").glob("*.pptx"))) == 3
PY
DOC_ID="$(python - <<"PY"
import json
from pathlib import Path
batch_dir = sorted(Path(".sisyphus/tmp/task14/happy/artifacts").iterdir())[0]
manifest = json.loads((batch_dir / "batch_manifest.json").read_text())
print(next(d for d in manifest["documents"] if d["input_file"].endswith("doc-a.pdf"))["doc_id"])
PY
)";
RUN_DIR="$(python - <<"PY"
from pathlib import Path
batch_dir = sorted(Path(".sisyphus/tmp/task14/happy/artifacts").iterdir())[0]
doc_id = Path("/dev/stdin").read_text().strip()
print(batch_dir / "docs" / doc_id)
PY
<<< "$DOC_ID")";
export DOC_ID RUN_DIR;
uv run python -m pptx_agent.cli revise --run-dir "$RUN_DIR" --feedback fixtures/feedback_patch_revise_valid.json;
python - <<"PY"
import json
import os
from pathlib import Path
run_dir = Path(os.environ["RUN_DIR"])
manifest = json.loads((run_dir / "run_manifest.json").read_text())
assert manifest["status"] == "pass"
assert manifest["targeted_slide_ids"] == ["slide_001"]
PY'
```

Failure guard pack (each command must exit non-zero with the expected reason):

```bash
# Guard 1: cloud profile without credential fails fast
env -u OPENAI_API_KEY uv run python -m pptx_agent.cli run-folder \
  --in-dir fixtures/rfp_input \
  --out-dir .sisyphus/tmp/task14/fail-cloud/out \
  --artifacts-root .sisyphus/tmp/task14/fail-cloud/artifacts \
  --model-profile cloud
# expected stderr contains: OPENAI_API_KEY is required for model-profile=cloud

# Guard 2: revise rejects invalid feedback target
DOC_ID="$(python - <<'PY'
import json
from pathlib import Path
batch_dir = sorted(Path('.sisyphus/tmp/task14/happy/artifacts').iterdir())[0]
manifest = json.loads((batch_dir / 'batch_manifest.json').read_text())
print(next(d for d in manifest['documents'] if d['input_file'].endswith('doc-a.pdf'))['doc_id'])
PY
)"
RUN_DIR="$(python - <<'PY'
from pathlib import Path
batch_dir = sorted(Path('.sisyphus/tmp/task14/happy/artifacts').iterdir())[0]
doc_id = Path('/dev/stdin').read_text().strip()
print(batch_dir / 'docs' / doc_id)
PY
<<< "$DOC_ID")"
uv run python -m pptx_agent.cli revise \
  --run-dir "$RUN_DIR" \
  --feedback fixtures/feedback_patch_revise_invalid_unknown_slide.json
# expected stderr contains: unknown_target
```

## MCP Surface Notes

MCP tool surface for this flow is constrained to `run-folder`, `analysis-summary`, and `revise` with allowlist and workspace path policy checks. Operator CLI runbook above remains the canonical manual path.
