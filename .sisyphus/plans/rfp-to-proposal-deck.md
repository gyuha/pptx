# RFP to Proposal Deck Pipeline (Folder + Iteration)

## TL;DR
> **Summary**: Expand the current deterministic single-PDF pipeline into a folder-based RFP analyzer that generates one proposal PPTX per input document, with evidence-grounded claims and a manual feedback revision loop.
> **Deliverables**:
> - `run-folder` orchestration for input/output directories
> - Evidence-first contracts (`corpus`, `evidence_graph`, `deck_outline`, `feedback_patch`, `batch_manifest`)
> - Proposal generation pipeline (analyze -> outline -> render -> qa)
> - Manual revision command (`revise`) with targeted patching
> - Skills/MCP/agent policy updates for new flow
> **Effort**: XL
> **Parallel**: YES - 5 waves
> **Critical Path**: T1 Contracts -> T2 Folder Orchestrator -> T6 Evidence Graph -> T7 Outline Planner -> T8 Render -> T9 QA -> T10 Revision Loop

## Context
### Original Request
- Input folder에 여러 RFP 문서를 넣으면 output folder에 사업제안서 `.pptx`를 자동 생성
- 단순 변환이 아니라 RFP 분석 기반 제안서 생성
- 지속적인 PPTX 개선 흐름 필요
- 필요시 skill/MCP/hook/agent 구성 확장

### Interview Summary
- Output mode: **문서별 1개 PPTX**
- Improvement loop: **수동 피드백 기반**
- Model policy: **선택형 프로파일 (local/cloud)**
- Existing constraints to preserve: deterministic artifacts, strict contract validation, hook/QA gate non-bypass

### Metis Review (gaps addressed)
- Added explicit guardrails against scope creep (no autonomous retraining, no full-regeneration-only loop)
- Added deterministic batch ordering and per-doc traceability requirements
- Added citation/provenance fail-closed acceptance criteria
- Added backward-compat criteria for existing `run-local`
- Added explicit minimum policy/security controls for cloud profile

## Work Objectives
### Core Objective
Enable reliable RFP-to-proposal generation where each input document yields one proposal deck with traceable evidence, deterministic artifacts, and iterative manual refinement.

### Deliverables
- New contracts for corpus/evidence/outline/revision/batch
- Folder orchestration command and output structure
- RFP analysis + requirement extraction stage
- Proposal outline and deterministic render stage
- Enhanced QA gates with citation coverage and contradiction checks
- Manual revision command with targeted slide patching
- Skills/MCP/agent policy updates aligned to new stages

### Definition of Done (verifiable conditions with commands)
- `uv run python -m pptx_agent.cli run-folder --in-dir fixtures/rfp_input --out-dir output --artifacts-root artifacts/batches --model-profile local` exits `0` and generates one PPTX per input file
- Batch artifact exists: `artifacts/batches/<batch_id>/batch_manifest.json` with schema and per-doc statuses
- Each output doc run contains `qa.preflight.json`, `qa.postrender.json`, `run_manifest.json`, and citation/provenance checks pass
- Generated proposal slide text and titles are Korean by default (`language=ko-KR`) unless an explicit per-run override is provided
- Slides requiring visuals include images generated via configured LLM image API and store prompt/model metadata in artifacts/manifest
- `uv run python -m pptx_agent.cli revise --run-dir artifacts/batches/<batch_id>/docs/<doc_id> --feedback fixtures/feedback/<doc_id>.patch.json` only updates targeted slides and revalidates QA
- Existing command `uv run python -m pptx_agent.cli run-local --in fixtures/extract/born_digital_sample.pdf --artifacts-root artifacts` remains compatible

### Must Have
- Deterministic ordering of folder inputs and stable `doc_id` assignment
- Evidence-first 2-pass: extraction/normalization -> evidence graph -> deck outline -> render
- Every claimable content block in slides references evidence IDs
- QA fail-closed on missing citation coverage, unsafe text, critical overflow, and contract mismatch
- Manual feedback loop as targeted patch (not blanket regeneration)
- Local/cloud model profile switch with explicit runtime profile recorded in manifest
- Default operation policy is fixed: `model-profile=local`, `continue-on-error=true`, final `run-folder` exit code is `1` if any doc fails (even when continuing)
- Default proposal structure is fixed: sections `Problem, Scope, Approach, Delivery Plan, Timeline, Pricing Assumptions, Risks, Differentiators, Next Steps`; target slide count 10-14 (hard fail outside 8-18)
- Default output language is Korean for all proposal slides, section headings, and summaries; non-Korean output requires explicit runtime option/feedback patch intent
- Image-bearing slides use LLM image generation API (no static stock fallback by default), with per-image prompt/model/seed(or null) trace captured in artifacts

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No silent fallback to uncited generated claims
- No bypass of `pre_render_contract_gate` or `post_render_qa_gate`
- No cross-folder evidence leakage
- No automatic infinite retry/self-improvement loop
- No writing outputs outside configured artifact/output roots

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after using existing CLI command assertions + JSON artifact assertions
- QA policy: every task includes happy and failure scenarios
- Evidence path convention: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave.

Wave 1: Contracts + orchestration foundations (T1, T2, T3)
Wave 2: Analysis and planning layers (T4, T5, T6, T7)
Wave 3: Rendering + gate hardening + iteration (T8, T9, T10)
Wave 4: Profiles + MCP/skills/agents integration (T11, T12, T13)
Wave 5: Fixtures, docs, regression validation (T14)

### Dependency Matrix (full)
- T1 -> blocks T2,T4,T5,T6,T7,T9,T10,T11,T12,T14
- T2 -> blocks T8,T9,T10,T11,T14
- T3 -> blocks T4,T5,T6
- T4 -> blocks T6,T7
- T5 -> blocks T6,T7,T9
- T6 -> blocks T7,T9,T10
- T7 -> blocks T8,T9,T10
- T8 -> blocks T9,T10,T14
- T9 -> blocks T10,T14
- T10 -> blocks T14
- T11 -> blocks T13,T14
- T12 -> blocks T13,T14
- T13 -> blocks T14

### Agent Dispatch Summary
- Wave 1: 3 tasks (architecture/contracts + CLI orchestration)
- Wave 2: 4 tasks (extraction/analysis/planning)
- Wave 3: 3 tasks (render/qa/revision loop)
- Wave 4: 3 tasks (profiles + MCP + agent policy)
- Wave 5: 1 task (fixtures/docs/regression)

## TODOs
> Implementation + Test = ONE task.
> Every task must include agent profile, references, acceptance, and QA scenarios.

- [x] 1. Define Additive Contracts for Corpus/Evidence/Outline/Revision

  **What to do**: Add schema models under `pptx_agent/contracts/` for `corpus.v1`, `evidence_graph.v1`, `deck_outline.v1`, `feedback_patch.v1`, `batch_manifest.v1`; keep existing `slidespec.v1` backward-compatible.
  **Must NOT do**: Do not break existing `SlideSpec` required provenance fields.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: contract design with strict compatibility constraints.
  - Skills: `python-expert`, `context-master` - enforce typed schema and dependency mapping.
  - Omitted: `visual-engineering` - not UI work.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,4,5,6,7,9,10,11,12,14 | Blocked By: none

  **References**:
  - Pattern: `pptx_agent/contracts/slidespec.py` - strict schema + provenance enforcement baseline
  - API/Type: `pptx_agent/normalize/payload.py` - normalized payload structure compatibility target
  - Test: `.sisyphus/evidence/task-2-slidespec.txt` - contract gate evidence pattern

  **Acceptance Criteria**:
  - [ ] `uv run python -m pptx_agent.cli validate-ir --in fixtures/slidespec_valid.json` still exits `0`
  - [ ] New contract fixtures validate and serialize deterministically (`sort_keys=True` where used)

  **QA Scenarios**:
  ```bash
  Scenario: Happy path contract validation
    Tool: Bash
    Steps: run contract fixture validation command for each new schema fixture
    Expected: exit 0 and schema_version matches expected v1 tokens
    Evidence: .sisyphus/evidence/task-1-contracts.txt

  Scenario: Failure/edge case contract rejection
    Tool: Bash
    Steps: validate malformed corpus/evidence/feedback fixture missing required fields
    Expected: non-zero exit with explicit field path errors
    Evidence: .sisyphus/evidence/task-1-contracts-error.txt
  ```

  **Commit**: YES | Message: `feat(contracts): add corpus/evidence/outline/revision schemas` | Files: `pptx_agent/contracts/*`, `fixtures/*`

- [x] 2. Add Folder-Oriented Orchestrator Command (`run-folder`)

  **What to do**: Extend `pptx_agent/cli.py` with `run-folder --in-dir --out-dir --artifacts-root --model-profile`; process supported docs in deterministic sorted order; one output PPTX per input doc.
  **Must NOT do**: Do not alter `run-local` semantics.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: orchestration and deterministic lifecycle handling.
  - Skills: `python-expert`, `context-master`.
  - Omitted: `react` - irrelevant.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 8,9,10,11,14 | Blocked By: 1

  **References**:
  - Pattern: `pptx_agent/cli.py` - current `run-local` deterministic artifact flow
  - API/Type: `pptx_agent/hooks/policy.py` - gate invocation integration points
  - Test: `.sisyphus/evidence/task-10-e2e.txt` - end-to-end evidence style

  **Acceptance Criteria**:
  - [ ] `run-folder` exits `0` for valid fixture directory and writes `batch_manifest.json`
  - [ ] Produced output decks count equals input supported-doc count
  - [ ] Existing `run-local` happy path remains pass

  **QA Scenarios**:
  ```bash
  Scenario: Happy path folder run
    Tool: Bash
    Steps: execute run-folder on fixtures/rfp_input with 3 valid docs
    Expected: 3 pptx files in output dir and batch manifest failed_count=0
    Evidence: .sisyphus/evidence/task-2-run-folder.txt

  Scenario: Failure/edge case unsupported file in folder
    Tool: Bash
    Steps: include unsupported file and rerun with continue-on-error policy
    Expected: batch manifest marks doc failure with reason; overall command policy matches spec
    Evidence: .sisyphus/evidence/task-2-run-folder-error.txt
  ```

  **Commit**: YES | Message: `feat(cli): add deterministic run-folder orchestration` | Files: `pptx_agent/cli.py`, `README.md`

- [x] 3. Implement Document Registry and Deterministic `doc_id`

  **What to do**: Add registry utility for file hash, stable `doc_id`, input metadata (name/type/size/hash) and per-batch catalog.
  **Must NOT do**: Do not use non-deterministic UUID for core identifiers.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: utility-level deterministic ID implementation.
  - Skills: `python-expert`.
  - Omitted: `testing` (not primary but add checks in task itself).

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 4,5,6 | Blocked By: 1

  **References**:
  - Pattern: `pptx_agent/normalize/payload.py` - current deterministic hashing style
  - API/Type: `pptx_agent/cli.py` - run_id/artifact path derivation logic

  **Acceptance Criteria**:
  - [ ] Same input folder order variations produce same `doc_id` assignments
  - [ ] Registry file written under batch artifacts

  **QA Scenarios**:
  ```bash
  Scenario: Happy path deterministic registry
    Tool: Bash
    Steps: run run-folder twice on same fixtures with cleaned outputs
    Expected: registry doc_id mapping identical between runs
    Evidence: .sisyphus/evidence/task-3-doc-registry.txt

  Scenario: Failure/edge case duplicate filename different content
    Tool: Bash
    Steps: include two docs with same basename but different bytes
    Expected: unique doc_id values and no overwrite in artifacts/output
    Evidence: .sisyphus/evidence/task-3-doc-registry-error.txt
  ```

  **Commit**: YES | Message: `feat(core): add deterministic document registry` | Files: `pptx_agent/*`, `fixtures/*`

- [x] 4. Extend Extraction to Mixed Docs (PDF + DOCX) with Unified Payload

  **What to do**: Add DOCX extractor adapter and dispatch in extraction stage; emit unified `extract.v1`-compatible structure with doc metadata.
  **Must NOT do**: Do not degrade current PDF extraction fallback behavior.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: parser adapters + contract consistency.
  - Skills: `python-expert`, `debugger`.
  - Omitted: `desktop`.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6,7 | Blocked By: 1,3

  **References**:
  - Pattern: `pptx_agent/extract/pdf.py` - PDF extraction and unsupported classification
  - API/Type: `pptx_agent/extract/__init__.py` - extractor exports
  - Test: `.sisyphus/evidence/task-3-extract.json`

  **Acceptance Criteria**:
  - [ ] PDF and DOCX samples both produce valid extraction JSON
  - [ ] Unsupported documents still emit deterministic unsupported reason codes

  **QA Scenarios**:
  ```bash
  Scenario: Happy path mixed extraction
    Tool: Bash
    Steps: run extract on sample PDF and sample DOCX fixtures
    Expected: both outputs validate against extract schema
    Evidence: .sisyphus/evidence/task-4-mixed-extract.txt

  Scenario: Failure/edge case corrupt DOCX
    Tool: Bash
    Steps: run extract on intentionally corrupt DOCX fixture
    Expected: non-zero exit or unsupported status with explicit reason code
    Evidence: .sisyphus/evidence/task-4-mixed-extract-error.txt
  ```

  **Commit**: YES | Message: `feat(extract): support docx ingestion with unified payload` | Files: `pptx_agent/extract/*`, `pyproject.toml`

- [x] 5. Upgrade Normalize for Corpus Context and Requirement Records

  **What to do**: Add `source_document_id`, requirement-classified elements, and corpus-level unsupported summary while preserving provenance coverage checks.
  **Must NOT do**: Do not remove existing required provenance fields.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: data-shape evolution with compatibility checks.
  - Skills: `python-expert`.
  - Omitted: `modal`.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6,7,9 | Blocked By: 1,3

  **References**:
  - Pattern: `pptx_agent/normalize/payload.py` - deterministic IDs + coverage metrics
  - API/Type: `pptx_agent/contracts/slidespec.py` - downstream provenance expectation

  **Acceptance Criteria**:
  - [ ] Normalized output includes document-level provenance and requirement tags
  - [ ] Coverage metric remains computable and validated

  **QA Scenarios**:
  ```bash
  Scenario: Happy path normalized corpus payload
    Tool: Bash
    Steps: normalize mixed extraction outputs into corpus-aware normalized payload
    Expected: status ok and required new fields present for each element
    Evidence: .sisyphus/evidence/task-5-normalize-corpus.txt

  Scenario: Failure/edge case missing source_document_id
    Tool: Bash
    Steps: validate malformed normalized fixture without source_document_id
    Expected: validation fails with field path
    Evidence: .sisyphus/evidence/task-5-normalize-corpus-error.txt
  ```

  **Commit**: YES | Message: `feat(normalize): add corpus-aware requirement normalization` | Files: `pptx_agent/normalize/*`, `fixtures/*`

- [x] 6. Build Evidence Graph and Claim Reference Mapping

  **What to do**: Introduce evidence graph builder that indexes requirement chunks and emits `evidence_graph.v1`; enforce claim-to-evidence ID linking inputs for planner.
  **Must NOT do**: Do not allow planner inputs without evidence IDs.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: trust-critical traceability layer.
  - Skills: `python-expert`, `debugger`.
  - Omitted: `frontend-ui-ux`.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 7,9,10 | Blocked By: 1,4,5

  **References**:
  - Pattern: `pptx_agent/plan/payload.py` - planning entrypoint location
  - API/Type: `pptx_agent/normalize/payload.py` - element provenance source
  - External: Oracle guidance (session `ses_36fea18deffehLbQ1A1H9z8SKB`) - evidence-first two-pass

  **Acceptance Criteria**:
  - [ ] Evidence graph output contains stable evidence IDs with doc/page/span provenance
  - [ ] Planner rejects claims not linked to evidence IDs

  **QA Scenarios**:
  ```bash
  Scenario: Happy path evidence graph generation
    Tool: Bash
    Steps: build evidence graph from normalized corpus fixture
    Expected: evidence graph schema valid and references all required claims
    Evidence: .sisyphus/evidence/task-6-evidence-graph.txt

  Scenario: Failure/edge case orphan claim
    Tool: Bash
    Steps: submit planner input with claim referencing missing evidence_id
    Expected: non-zero failure with explicit orphan evidence error
    Evidence: .sisyphus/evidence/task-6-evidence-graph-error.txt
  ```

  **Commit**: YES | Message: `feat(plan): add evidence graph and claim grounding checks` | Files: `pptx_agent/plan/*`, `pptx_agent/contracts/*`

- [x] 7. Implement Proposal Deck Outline Planner (`deck_outline.v1`)

  **What to do**: Add proposal planner stage that synthesizes business-proposal sections (problem, approach, delivery, risk, differentiators, timeline, pricing assumptions) into `deck_outline.v1`, then map to `slidespec.v1`.
  **Must NOT do**: Do not allow uncited numeric facts in outline claims.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: content synthesis + strict schema outputs.
  - Skills: `python-expert`, `context-master`.
  - Omitted: `testing` (covered within task).

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 8,9,10 | Blocked By: 1,4,5,6

  **References**:
  - Pattern: `pptx_agent/plan/payload.py` - existing normalized->slidespec transform
  - API/Type: `pptx_agent/contracts/slidespec.py` - final render contract
  - External: Librarian guidance (session `ses_36fea193dffeK9Ayq6CgkUKYo3`) - deck_outline control artifact

  **Acceptance Criteria**:
  - [ ] Outline generation emits required section intents and evidence IDs
  - [ ] Slidespec conversion preserves evidence/provenance per element

  **QA Scenarios**:
  ```bash
  Scenario: Happy path proposal outline
    Tool: Bash
    Steps: generate deck outline and convert to slidespec for sample RFP
    Expected: mandatory sections present and slidespec validates
    Evidence: .sisyphus/evidence/task-7-outline.txt

  Scenario: Failure/edge case missing mandatory section
    Tool: Bash
    Steps: validate outline fixture without risk section
    Expected: non-zero validation failure with missing section error
    Evidence: .sisyphus/evidence/task-7-outline-error.txt
  ```

  **Commit**: YES | Message: `feat(plan): add proposal deck outline synthesis` | Files: `pptx_agent/plan/*`, `fixtures/*`

- [x] 8. Render One Proposal Deck per Document into Output Folder

  **What to do**: Wire renderer to consume generated slidespec per `doc_id` and write final `.pptx` under `output/`; keep deterministic layout and naming convention. Add LLM image API generation for visual slides and insert generated images into PPTX.
  **Must NOT do**: Do not generate single combined portfolio deck in this scope.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: render wiring + output policy.
  - Skills: `python-expert`.
  - Omitted: `tailwindcss-*`.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 9,10,14 | Blocked By: 2,7

  **References**:
  - Pattern: `pptx_agent/render/pptx.py` - deterministic layout logic
  - API/Type: `pptx_agent/cli.py` - output path handling in run-local

  **Acceptance Criteria**:
  - [ ] For each input doc, one output PPTX file exists in configured output folder
  - [ ] Render QA report generated per doc
  - [ ] Visual slides include generated image assets from LLM API and manifest stores `image_prompt`, `image_model`, `image_seed` (nullable), and image file path

  **QA Scenarios**:
  ```bash
  Scenario: Happy path per-doc render
    Tool: Bash
    Steps: run-folder on 3-doc fixture set
    Expected: output dir has exactly 3 pptx files with matching doc_ids and at least one generated image per deck where visual intent exists
    Evidence: .sisyphus/evidence/task-8-render-per-doc.txt

  Scenario: Failure/edge case unsupported layout hint
    Tool: Bash
    Steps: render slidespec with invalid layout_hint
    Expected: non-zero exit with unsupported-layout reason and hook error artifact
    Evidence: .sisyphus/evidence/task-8-render-per-doc-error.txt

  Scenario: Failure/edge case image API error
    Tool: Bash
    Steps: run render with invalid image API credential/profile
    Expected: non-zero exit with explicit `image_generation_failed` reason and hook error artifact
    Evidence: .sisyphus/evidence/task-8-render-image-error.txt
  ```

  **Commit**: YES | Message: `feat(render): emit one proposal pptx per input document` | Files: `pptx_agent/render/*`, `pptx_agent/cli.py`

- [x] 9. Extend QA Gates for Citation/Contradiction/Proposal Checks

  **What to do**: Enhance QA gate report to include citation coverage completeness, uncited numeric fact check, and basic contradiction detection across key claims.
  **Must NOT do**: Do not weaken existing checks (`unsafe_text_absent`, overflow, hook summary).

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: safety/trust gates define release quality.
  - Skills: `python-expert`, `debugger`, `testing`.
  - Omitted: `react`.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 10,14 | Blocked By: 1,2,5,6,7,8

  **References**:
  - Pattern: `pptx_agent/cli.py` - `_build_qa_gate_report`
  - API/Type: `pptx_agent/hooks/policy.py` - post-render qa gate enforcement
  - Test: `artifacts/b611d124a215514e/qa.postrender.json` - existing qa schema behavior

  **Acceptance Criteria**:
  - [ ] QA report includes new citation/contradiction checks with binary pass/fail
  - [ ] Missing citation triggers non-zero gate failure

  **QA Scenarios**:
  ```bash
  Scenario: Happy path citation-complete deck
    Tool: Bash
    Steps: run qa on generated cited slidespec + reports
    Expected: status pass with citation checks true
    Evidence: .sisyphus/evidence/task-9-qa-citation.txt

  Scenario: Failure/edge case uncited numeric claim
    Tool: Bash
    Steps: run qa on fixture containing numeric fact without evidence linkage
    Expected: status fail and explicit uncited_numeric_fact failure entry
    Evidence: .sisyphus/evidence/task-9-qa-citation-error.txt
  ```

  **Commit**: YES | Message: `feat(qa): add citation and contradiction quality gates` | Files: `pptx_agent/cli.py`, `pptx_agent/hooks/*`

- [x] 10. Add Manual Feedback Revision Loop (`revise`)

  **What to do**: Add `revise --run-dir --feedback` command consuming `feedback_patch.v1` to patch targeted slides/sections, then re-run validate/qa/render for impacted doc only.
  **Must NOT do**: Do not regenerate unaffected slides.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: selective mutation + deterministic rerun boundary.
  - Skills: `python-expert`, `debugger`, `testing`.
  - Omitted: `artistry`.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 14 | Blocked By: 2,6,7,8,9

  **References**:
  - Pattern: `pptx_agent/cli.py` - run orchestration and artifact manifests
  - API/Type: `pptx_agent/contracts/slidespec.py` - patch target schema integrity
  - External: Oracle guidance - targeted patch loop, no full free-form regeneration

  **Acceptance Criteria**:
  - [ ] Revision run updates only targeted slide IDs
  - [ ] New run manifest records parent_run_id + feedback reference

  **QA Scenarios**:
  ```bash
  Scenario: Happy path targeted revision
    Tool: Bash
    Steps: apply feedback patch modifying one slide objective and rerun revise
    Expected: only targeted slide content differs; qa postrender pass
    Evidence: .sisyphus/evidence/task-10-revise.txt

  Scenario: Failure/edge case feedback references unknown slide_id
    Tool: Bash
    Steps: run revise with invalid patch target
    Expected: non-zero failure with explicit unknown_target error and no render output overwrite
    Evidence: .sisyphus/evidence/task-10-revise-error.txt
  ```

  **Commit**: YES | Message: `feat(cli): add manual feedback revision loop` | Files: `pptx_agent/cli.py`, `pptx_agent/contracts/*`

- [x] 11. Implement Model Profile Layer (`local|cloud`) with Manifest Trace

  **What to do**: Add model profile config surface and runtime selection; record profile and generation settings hash in per-doc manifest. Include text model and image model API settings.
  **Must NOT do**: Do not hardcode cloud credential requirements for local profile.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: runtime configuration and safety boundaries.
  - Skills: `add-setting-env`, `python-expert`.
  - Omitted: `desktop`.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 13,14 | Blocked By: 1,2

  **References**:
  - Pattern: `pyproject.toml` and CLI flag handling in `pptx_agent/cli.py`
  - API/Type: current `run_manifest.json` structure under `artifacts/*/run_manifest.json`

  **Acceptance Criteria**:
  - [ ] Local profile works with no cloud env vars
  - [ ] Cloud profile fails fast with clear missing-credential message when required env absent
  - [ ] Manifest records selected profile
  - [ ] Manifest records image-generation provider/model and per-run image generation stats (requested/succeeded/failed)

  **QA Scenarios**:
  ```bash
  Scenario: Happy path local profile
    Tool: Bash
    Steps: run-folder with --model-profile local
    Expected: success and manifest profile=local
    Evidence: .sisyphus/evidence/task-11-model-profile.txt

  Scenario: Failure/edge case cloud profile without creds
    Tool: Bash
    Steps: unset cloud env vars and run-folder with --model-profile cloud
    Expected: non-zero exit with missing credential error
    Evidence: .sisyphus/evidence/task-11-model-profile-error.txt
  ```

  **Commit**: YES | Message: `feat(config): add local-cloud model profile selection` | Files: `pptx_agent/cli.py`, `README.md`

- [x] 12. Extend MCP Tools for Corpus and Revision Operations

  **What to do**: Add safe MCP operations for `run-folder`/analysis summary/revision trigger while preserving strict allowlist and schema validation.
  **Must NOT do**: Do not expose unrestricted filesystem operations.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: API surface governance.
  - Skills: `python-expert`, `code-reviewer`.
  - Omitted: `playwright`.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 13,14 | Blocked By: 1,2

  **References**:
  - Pattern: `pptx_agent/mcp/server.py` - current approved operations + validation flow
  - API/Type: `pptx_agent/agents/role_profiles.json` - tool allowlists

  **Acceptance Criteria**:
  - [ ] New MCP tools are schema-validated and deterministic
  - [ ] Unapproved operation requests still return `-32601`

  **QA Scenarios**:
  ```bash
  Scenario: Happy path MCP folder run call
    Tool: Bash
    Steps: send JSON-RPC tools/call for approved new operation
    Expected: success result with deterministic payload
    Evidence: .sisyphus/evidence/task-12-mcp.txt

  Scenario: Failure/edge case unapproved tool call
    Tool: Bash
    Steps: send JSON-RPC tools/call with non-approved operation name
    Expected: error code -32601 and policy message
    Evidence: .sisyphus/evidence/task-12-mcp-error.txt
  ```

  **Commit**: YES | Message: `feat(mcp): add corpus and revision operations safely` | Files: `pptx_agent/mcp/server.py`, `fixtures/*`

- [x] 13. Update Agent Roles, Skills, and Orchestration Dry-Run for New Flow

  **What to do**: Expand role profiles, orchestration dry-run, and skill wiring docs for added stages (corpus analysis, outline, revision loop, batch manager).
  **Must NOT do**: Do not permit role bypass of QA/hook gates.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: policy and orchestration configuration clarity.
  - Skills: `context-master`, `project-planner`.
  - Omitted: `react`.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 14 | Blocked By: 11,12

  **References**:
  - Pattern: `pptx_agent/agents/role_profiles.json`
  - Pattern: `pptx_agent/agents/orchestration_dry_run.json`
  - Pattern: `pptx_agent/agents/skill_wiring.md`

  **Acceptance Criteria**:
  - [ ] Dry-run orchestration validates stage handoff sequence for new commands
  - [ ] Role policies enforce approved tool subsets for each role

  **QA Scenarios**:
  ```bash
  Scenario: Happy path role dry-run
    Tool: Bash
    Steps: run dry-run validation against updated orchestration config
    Expected: pass with no policy violations
    Evidence: .sisyphus/evidence/task-13-agents.txt

  Scenario: Failure/edge case forbidden role action
    Tool: Bash
    Steps: execute simulated forbidden operation under restricted role
    Expected: policy rejection with non-zero exit and explicit reason
    Evidence: .sisyphus/evidence/task-13-agents-error.txt
  ```

  **Commit**: YES | Message: `chore(agents): align role policy with rfp proposal workflow` | Files: `pptx_agent/agents/*`

- [ ] 14. Add End-to-End Fixtures, Runbook, and Regression Validation Pack

  **What to do**: Create fixture sets for folder mode and feedback patches; update README with operator runbook for run-folder/revise/model profiles; add deterministic regression command set.
  **Must NOT do**: Do not remove existing canonical `run-local` documentation.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: runbook + evidence reproducibility.
  - Skills: `testing`, `context-master`.
  - Omitted: `frontend-ui-ux`.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: none | Blocked By: 1,2,8,9,10,11,12,13

  **References**:
  - Pattern: `README.md` - existing canonical local runbook
  - Test: `.sisyphus/evidence/task-10-e2e.txt` - E2E evidence style

  **Acceptance Criteria**:
  - [ ] README contains complete copy-paste runbook for folder run + revision loop
  - [ ] Regression command pack reproduces happy and failure paths deterministically

  **QA Scenarios**:
  ```bash
  Scenario: Happy path regression pack
    Tool: Bash
    Steps: run documented regression sequence end-to-end
    Expected: all pass commands exit 0 and expected artifacts present
    Evidence: .sisyphus/evidence/task-14-regression.txt

  Scenario: Failure/edge case regression guard
    Tool: Bash
    Steps: run documented malformed feedback/citation-missing case
    Expected: expected command exits non-zero with documented failure reason
    Evidence: .sisyphus/evidence/task-14-regression-error.txt
  ```

  **Commit**: YES | Message: `docs(runbook): add rfp folder workflow and revision regression` | Files: `README.md`, `fixtures/*`, `.sisyphus/evidence/*`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle
- [ ] F2. Code Quality Review - unspecified-high
- [ ] F3. Real Manual QA - unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check - deep

## Commit Strategy
- Use atomic commits per task group (contracts/orchestrator/analysis/render/qa/policies/docs)
- Commit only after task acceptance + QA evidence file is written
- Preserve backward compatibility checkpoints with explicit commit messages

## Success Criteria
- Folder-based per-document proposal generation works deterministically
- Every proposal claim is evidence-grounded and citation-validated
- Manual feedback revision updates only targeted content and re-passes QA
- Local/cloud profile choice is explicit and traceable in manifests
- Existing single-document runbook still works without behavior regression
- Proposal deck text is generated in Korean by default across outline and rendered slides
- Proposal deck visual slides include images generated via LLM API with traceable prompt/model metadata
