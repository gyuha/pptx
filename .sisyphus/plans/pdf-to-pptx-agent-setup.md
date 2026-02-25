# PDF to PPTX Agent Setup (Local MVP)

## TL;DR
> **Summary**: Build a Python-first local MVP pipeline that converts reference PDFs into PPTX using a strict SlideSpec contract, typed MCP tools, controlled hooks, and focused subagents.
> **Deliverables**:
> - Python project bootstrap with pinned dependencies
> - SlideSpec v1 schema and validator
> - Extract -> plan -> render -> QA pipeline
> - Hook policies and MCP tool surface
> - Skills/subagent configuration and runnable local smoke flow
> **Effort**: Large
> **Parallel**: YES - 2 waves
> **Critical Path**: 1 -> 2 -> 3 -> 4 -> 6 -> 10

## Context
### Original Request
- Build an agent that uses reference PDF files and skills/MCP/hooks/agents to generate PPTX, and install the required components.

### Interview Summary
- Runtime: Python-first.
- Package manager/runtime tooling default: `uv` + `pyproject.toml` + `uv.lock`.
- Scope: Local MVP first (CI deferred).
- Test decision: Tests-after.
- Execution style: ultrawork-compatible decomposition (`--ulw`).

### Metis Review (gaps addressed)
- Added strict SlideSpec contract-first approach.
- Added unsupported-input matrix and fail policy.
- Added provenance requirements (`source_page`, evidence linkage, confidence).
- Added deterministic artifact layout and non-interactive acceptance commands.
- Added guardrails against agent overreach and broad MCP exposure.

## Work Objectives
### Core Objective
- Produce a decision-complete installation and implementation path for a local agentic pipeline that converts PDFs to PPTX with auditable provenance.

### Deliverables
- Runnable local scaffold for extraction, planning, rendering, and QA.
- Typed SlideSpec v1 contract and validation gate.
- Minimal typed MCP server exposing only required operations.
- Hook policies enforcing safety and contract compliance.
- Skills/subagent definitions wired to the pipeline stages.

### Definition of Done (verifiable conditions with commands)
- `uv python find` resolves Python `>=3.11`.
- Dependency import smoke passes: `uv run python -c "import fitz, pdfplumber, pypdf, pptx, pydantic; print('ok')"`.
- CLI can execute `uv run python -m pptx_agent.cli {extract|validate-ir|plan|render|qa}` without manual steps.
- Generated `artifacts/<run_id>/slidespec.json` validates against SlideSpec v1.
- Generated `artifacts/<run_id>/output.pptx` passes QA thresholds (no critical overflow, no missing required text blocks).

### Must Have
- Single canonical IR: SlideSpec v1.
- Evidence/provenance attached to generated slide elements.
- Hook gates for pre-render and post-render validation.
- Typed MCP endpoints with narrow scope.
- Agent-executed QA scenarios for every task.
- Canonical local module path: `pptx_agent` (no alternate package roots).

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No direct render path bypassing SlideSpec validation.
- No broad filesystem/network shell tooling exposed through MCP.
- No silent auto-fix mutations in hooks.
- No CI setup in this MVP plan.
- No advanced design-system/theming engine in MVP.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after + Python smoke/contract/QA commands.
- QA policy: Every task includes happy + failure scenario with evidence path.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: bootstrap + contract + extraction + planning foundation (Tasks 1-5)
Wave 2: rendering + hooks + MCP + roles + end-to-end hardening (Tasks 6-10)

### Dependency Matrix (full, all tasks)
- 1: none
- 2: 1
- 3: 1,2
- 4: 2,3
- 5: 2,4
- 6: 2,5
- 7: 2,6
- 8: 2,3,6,7
- 9: 5,6,7,8
- 10: 3,4,6,7,8,9

### Agent Dispatch Summary (wave -> task count -> categories)
- Wave 1 -> 5 tasks -> quick, unspecified-high, deep
- Wave 2 -> 5 tasks -> deep, writing, unspecified-high

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Python Project Bootstrap and Dependency Pinning

  **What to do**: Initialize Python project structure with `uv`, `pyproject.toml`, `uv.lock`, and base CLI entrypoint `python -m pptx_agent.cli`. Pin Python `>=3.11` and core libs (`PyMuPDF`, `pdfplumber`, `pypdf`, `python-pptx`, `pydantic`).
  **Must NOT do**: Add CI workflows or cloud runtime integration.

  **Recommended Agent Profile**:
  - Category: `quick` — Reason: mechanical scaffold and dependency setup.
  - Skills: [`python-expert`] — Dependency/env structure best practices.
  - Omitted: [`modern-automation-patterns`] — CI/deploy is out of scope.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2,3,4,5,6,7,8,9,10] | Blocked By: []

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:1` — Repo is greenfield and requires first-principles bootstrap.
  - Pattern: `.sisyphus/drafts/pdf-to-pptx-agent-setup.md` — Confirmed decisions (Python-first, local MVP, tests-after).
  - External: `https://pymupdf.readthedocs.io/` — Extraction dependency guidance.
  - External: `https://python-pptx.readthedocs.io/en/latest/` — PPTX generation dependency guidance.

  **Acceptance Criteria** (agent-executable only):
  - [ ] `uv python find` resolves version `>=3.11`.
  - [ ] `uv sync` exits `0` and `uv.lock` exists.
  - [ ] `uv run python -c "import fitz, pdfplumber, pypdf, pptx, pydantic; print('ok')"` outputs `ok`.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path bootstrap
    Tool: Bash
    Steps: run `uv sync`, then run `uv run` import smoke command
    Expected: all commands exit 0, stdout includes "ok"
    Evidence: .sisyphus/evidence/task-1-bootstrap.txt

  Scenario: Failure path invalid Python version
    Tool: Bash
    Steps: run version guard with simulated <3.11 interpreter in preflight check
    Expected: script fails fast with clear version error message
    Evidence: .sisyphus/evidence/task-1-bootstrap-error.txt
  ```

  **Commit**: YES | Message: `chore(bootstrap): initialize python runtime and pinned dependencies` | Files: project manifest, lockfile, base package/cli files

- [ ] 2. Define SlideSpec v1 Contract and Validator

  **What to do**: Create canonical SlideSpec schema with required provenance fields (`source_page`, evidence link, confidence), validation rules, and a validator command.
  **Must NOT do**: Allow optional provenance for MVP-required slide elements.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: contract design and strict validation semantics.
  - Skills: [`python-expert`] — Pydantic/schema rigor.
  - Omitted: [`react`] — No frontend/UI scope.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [3,4,5,6,7,8,9,10] | Blocked By: [1]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — Contract-first architecture and guardrails.
  - Pattern: `.sisyphus/drafts/pdf-to-pptx-agent-setup.md` — Metis requirement for strict provenance.
  - External: `https://pydantic.dev/` — Typed model validation patterns.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Validator accepts a minimal valid SlideSpec fixture (exit `0`).
  - [ ] Validator rejects fixture missing provenance (non-zero + explicit field errors).
  - [ ] SlideSpec schema version field is mandatory and validated.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path valid SlideSpec
    Tool: Bash
    Steps: run validate command against valid fixture json
    Expected: exit 0 and output contains "SlideSpec v1 valid"
    Evidence: .sisyphus/evidence/task-2-slidespec.txt

  Scenario: Failure path missing source_page
    Tool: Bash
    Steps: run validate command against invalid fixture json
    Expected: non-zero exit and error names missing provenance field
    Evidence: .sisyphus/evidence/task-2-slidespec-error.txt
  ```

  **Commit**: YES | Message: `feat(contract): add slidespec v1 schema and validation cli` | Files: contract models, validation command, fixtures

- [ ] 3. Implement PDF Extraction Stage with Bounded Fallbacks

  **What to do**: Implement extractor that reads PDF text/layout with PyMuPDF first, uses pdfplumber for difficult table/geometry cases, and emits normalized extraction payload with confidence metadata.
  **Must NOT do**: Add OCR pipeline in MVP; instead flag scanned/unsupported docs.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: extraction reliability and fallback logic.
  - Skills: [`python-expert`] — robust parser orchestration.
  - Omitted: [`desktop`] — not relevant to local CLI pipeline.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [4,8,10] | Blocked By: [1,2]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — staged `extract -> normalize -> plan -> render -> qa` pipeline.
  - External: `https://pymupdf.readthedocs.io/` — primary extraction API.
  - External: `https://github.com/jsvine/pdfplumber/blob/stable/README.md` — geometry/table fallback.
  - External: `https://pypdf.readthedocs.io/en/stable/user/security.html` — parser safety constraints.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Extract command on born-digital sample PDF returns structured page/blocks JSON.
  - [ ] Unsupported/scanned PDF returns non-fatal unsupported classification with reason code.
  - [ ] No extraction run bypasses confidence assignment.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path born-digital extraction
    Tool: Bash
    Steps: run extract command on fixture PDF and save output json
    Expected: exit 0 and output includes pages, blocks, confidence fields
    Evidence: .sisyphus/evidence/task-3-extract.json

  Scenario: Failure/edge scanned PDF
    Tool: Bash
    Steps: run extract on scanned fixture without OCR enabled
    Expected: non-zero or unsupported status with explicit reason code
    Evidence: .sisyphus/evidence/task-3-extract-error.txt
  ```

  **Commit**: YES | Message: `feat(extract): add pdf extraction with controlled fallback paths` | Files: extractor modules, fixtures, extract CLI

- [ ] 4. Build Normalization and Provenance Mapping Stage

  **What to do**: Convert extraction payload into SlideSpec-ready normalized structures with stable IDs, source mapping, and unsupported-input matrix logging.
  **Must NOT do**: Invent content not present in extracted evidence.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: data-model normalization and provenance discipline.
  - Skills: [`python-expert`] — deterministic transforms.
  - Omitted: [`artistry`] — no unconventional approach needed.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [5,10] | Blocked By: [2,3]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — provenance and unsupported-input guardrails.
  - Pattern: `.sisyphus/drafts/pdf-to-pptx-agent-setup.md` — confirmed auditability requirement.
  - External: `https://modelcontextprotocol.io/specification` — typed payload discipline analog for downstream tools.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Normalize command emits deterministic IDs across repeated runs of same input hash.
  - [ ] 100% of normalized elements include source references and confidence.
  - [ ] Unsupported classes are reported in machine-readable matrix.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path normalization
    Tool: Bash
    Steps: run normalize on extractor output twice and compare deterministic fields
    Expected: IDs and source references are stable across runs
    Evidence: .sisyphus/evidence/task-4-normalize.txt

  Scenario: Failure path missing extraction metadata
    Tool: Bash
    Steps: run normalize on malformed extraction json missing page mapping
    Expected: non-zero exit with explicit validation error
    Evidence: .sisyphus/evidence/task-4-normalize-error.txt
  ```

  **Commit**: YES | Message: `feat(normalize): add deterministic provenance mapping stage` | Files: normalization module, unsupported matrix report, normalize CLI

- [ ] 5. Implement Slide Planning Stage (Content-to-Layout Intent)

  **What to do**: Build planner that transforms normalized evidence into slide intents (title/body/image/table blocks) with bounded layout hints and no style freeform drift.
  **Must NOT do**: Rewrite factual source content without evidence tie-back.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: balancing layout intent with evidence fidelity.
  - Skills: [`python-expert`] — deterministic planning logic and contracts.
  - Omitted: [`frontend-ui-ux`] — visual implementation is delegated to renderer templates.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [6,9,10] | Blocked By: [2,4]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — single IR and stage boundaries.
  - External: `https://docs.anthropic.com/en/docs/claude-code/sub-agents` — role separation patterns.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Plan command outputs SlideSpec-compliant slide entries for a sample normalized input.
  - [ ] Planner retains source references on every generated block.
  - [ ] Planner emits explicit low-confidence markers when extraction confidence is below threshold.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path slide planning
    Tool: Bash
    Steps: run plan command on normalized fixture
    Expected: valid SlideSpec output with slide intents and retained provenance
    Evidence: .sisyphus/evidence/task-5-plan.json

  Scenario: Failure/edge low-confidence input
    Tool: Bash
    Steps: run plan command on fixture with low-confidence extraction blocks
    Expected: output marks low-confidence blocks and does not silently upgrade confidence
    Evidence: .sisyphus/evidence/task-5-plan-error.json
  ```

  **Commit**: YES | Message: `feat(planner): add evidence-bound slide planning stage` | Files: planning module, plan CLI, fixtures

- [ ] 6. Implement PPTX Rendering Stage with Deterministic Template Rules

  **What to do**: Render SlideSpec into PPTX using python-pptx with deterministic style tokens/template mapping and overflow checks.
  **Must NOT do**: Inject random design choices or mutate content outside SlideSpec.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: precise mapping from IR to PPTX objects.
  - Skills: [`python-expert`] — python-pptx API reliability.
  - Omitted: [`tailwindcss-advanced-layouts`] — web CSS tooling is irrelevant.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [7,8,9,10] | Blocked By: [2,5]

  **References** (executor has NO interview context — be exhaustive):
  - External: `https://python-pptx.readthedocs.io/en/latest/` — rendering APIs and shape/text controls.
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — deterministic renderer guardrail.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Render command generates `.pptx` from valid SlideSpec with exit `0`.
  - [ ] Rendered deck slide count equals planned slide count.
  - [ ] Critical text overflow count in QA report is `0` for sample fixture.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path deterministic render
    Tool: Bash
    Steps: run render twice on same SlideSpec and compare deterministic QA fields
    Expected: same slide count/structure and stable QA metrics
    Evidence: .sisyphus/evidence/task-6-render.txt

  Scenario: Failure path invalid layout hint
    Tool: Bash
    Steps: run render on SlideSpec fixture with unsupported layout enum
    Expected: non-zero exit and explicit unsupported-layout error
    Evidence: .sisyphus/evidence/task-6-render-error.txt
  ```

  **Commit**: YES | Message: `feat(renderer): map slidespec to deterministic pptx output` | Files: renderer module, template rules, render CLI

- [ ] 7. Add Hook Policy Layer (Pre/Post/OnError)

  **What to do**: Implement hook execution points for pre-render contract gate, post-render QA gate, and on-error degraded-mode reporting.
  **Must NOT do**: Auto-correct invalid payloads silently; hooks must fail with explicit reason.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: policy enforcement and failure semantics.
  - Skills: [`debugger`] — robust error-path handling.
  - Omitted: [`autopilot`] — explicit control preferred over autonomous looping in MVP.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [8,9,10] | Blocked By: [2,6]

  **References** (executor has NO interview context — be exhaustive):
  - External: `https://docs.anthropic.com/en/docs/claude-code/hooks` — hook lifecycle and patterns.
  - External: `https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices` — policy and boundary controls.
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — no silent auto-fix guardrail.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Pre-render hook blocks invalid SlideSpec before render begins.
  - [ ] Post-render hook records QA summary artifact for successful runs.
  - [ ] On-error hook writes deterministic error report with run ID.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path hook chain
    Tool: Bash
    Steps: run full pipeline with valid fixture and hooks enabled
    Expected: pre/post hooks execute and produce QA report artifact
    Evidence: .sisyphus/evidence/task-7-hooks.txt

  Scenario: Failure path pre-render rejection
    Tool: Bash
    Steps: run render with invalid SlideSpec while hooks enabled
    Expected: pre-render hook blocks run with explicit validation error
    Evidence: .sisyphus/evidence/task-7-hooks-error.txt
  ```

  **Commit**: YES | Message: `feat(hooks): enforce pre-post policy gates for pipeline runs` | Files: hook framework, policy checks, error reporter

- [ ] 8. Implement Minimal Typed MCP Server Surface

  **What to do**: Add MCP server exposing only required typed tools/resources for `extract`, `plan`, `render`, and `qa`, with strict input/output schemas.
  **Must NOT do**: Expose unrestricted shell/filesystem/network operations.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: protocol boundary correctness and tool hardening.
  - Skills: [`plugin-master`] — MCP/tooling packaging conventions.
  - Omitted: [`ultrawork`] — this task focuses protocol correctness, not parallel orchestration.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [9,10] | Blocked By: [2,3,6,7]

  **References** (executor has NO interview context — be exhaustive):
  - External: `https://modelcontextprotocol.io/specification` — MCP protocol contract.
  - External: `https://modelcontextprotocol.io/docs/learn/architecture` — server/tool architecture patterns.
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — narrow typed MCP requirement.

  **Acceptance Criteria** (agent-executable only):
  - [ ] MCP server starts locally and advertises only approved tools.
  - [ ] Invalid tool payload fails schema validation with clear error.
  - [ ] End-to-end tool invocation can trigger extract->render path through MCP.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path typed MCP calls
    Tool: Bash
    Steps: start MCP server and invoke approved tools with valid payloads
    Expected: tool calls succeed and outputs match schema
    Evidence: .sisyphus/evidence/task-8-mcp.txt

  Scenario: Failure path blocked unsafe tool call
    Tool: Bash
    Steps: invoke non-approved/broad operation via MCP
    Expected: request denied with explicit policy/schema error
    Evidence: .sisyphus/evidence/task-8-mcp-error.txt
  ```

  **Commit**: YES | Message: `feat(mcp): add minimal typed server endpoints for pipeline stages` | Files: MCP server module, tool schemas, startup docs

- [ ] 9. Configure Skills and Specialized Subagent Profiles

  **What to do**: Define skill packages and subagent roles aligned to pipeline stages: `ContentAgent` (extract/normalize), `DesignAgent` (plan), `BuildAgent` (render), `QAAgent` (validate/report).
  **Must NOT do**: Allow agents to bypass hook gates or write outside approved pipeline artifacts.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: config/spec quality and role clarity.
  - Skills: [`context-master`, `plugin-master`] — context-efficient role boundaries and skill wiring.
  - Omitted: [`react`] — no UI implementation required.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [10] | Blocked By: [5,6,7,8]

  **References** (executor has NO interview context — be exhaustive):
  - External: `https://docs.anthropic.com/en/docs/claude-code/sub-agents` — subagent specialization model.
  - External: `https://docs.anthropic.com/en/docs/claude-code/hooks` — policy alignment for agent actions.
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — required stage boundaries and safety constraints.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Each subagent role has explicit scope, allowed tools, and forbidden actions.
  - [ ] Skill wiring maps one-to-one to pipeline stage responsibilities.
  - [ ] Dry-run orchestration path executes role handoff without missing config errors.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path role handoff
    Tool: Bash
    Steps: run orchestrated dry-run invoking all configured roles in order
    Expected: each stage completes and handoff payload validates
    Evidence: .sisyphus/evidence/task-9-agents.txt

  Scenario: Failure path unauthorized role action
    Tool: Bash
    Steps: trigger role to call disallowed operation outside its scope
    Expected: policy rejection with clear role-boundary error
    Evidence: .sisyphus/evidence/task-9-agents-error.txt
  ```

  **Commit**: YES | Message: `chore(agents): add stage-aligned skills and subagent role configs` | Files: skill specs, agent configs, orchestration mapping docs

- [ ] 10. End-to-End Local MVP Runbook, QA Gate, and Artifact Discipline

  **What to do**: Implement one canonical local command path from PDF input to PPTX output, enforce artifact layout (`artifacts/<run_id>/...`), and codify tests-after smoke/contract/qa checks in runbook scripts.
  **Must NOT do**: Depend on manual visual checks as acceptance gates.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: cross-component integration and verification hardening.
  - Skills: [`testing`, `python-expert`] — command-based QA and stable automation.
  - Omitted: [`playwright`] — CLI pipeline has no UI dependency for MVP acceptance.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [] | Blocked By: [3,4,6,7,8,9]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `.sisyphus/plans/pdf-to-pptx-agent-setup.md` — Definition of Done and artifact policy.
  - Pattern: `.sisyphus/drafts/pdf-to-pptx-agent-setup.md` — confirmed local MVP scope.
  - External: `https://owasp.org/www-project-cheat-sheets/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html` — handling untrusted extracted text.

  **Acceptance Criteria** (agent-executable only):
  - [ ] Single canonical sequence executes locally:
    `uv run python -m pptx_agent.cli extract` -> `validate-ir` -> `plan` -> `render` -> `qa`.
  - [ ] Run generates complete artifact set under one `run_id` directory.
  - [ ] QA summary indicates no critical failures and includes provenance coverage metrics.

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Happy path full local run
    Tool: Bash
    Steps: execute canonical runbook command on fixture PDF
    Expected: output.pptx and qa report created with pass status
    Evidence: .sisyphus/evidence/task-10-e2e.txt

  Scenario: Failure path malformed input and injection-like payload
    Tool: Bash
    Steps: run pipeline on malformed PDF or poisoned extracted text fixture
    Expected: pipeline fails safely with explicit validation/policy error and no partial unsafe output
    Evidence: .sisyphus/evidence/task-10-e2e-error.txt
  ```

  **Commit**: YES | Message: `feat(e2e): add local mvp runbook with qa and artifact gates` | Files: run scripts, QA reporter, artifact policy docs

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit in small atomic units aligned to tasks 1-10.
- Commit message format: `type(scope): desc`.
- No amend; no force operations.

## Success Criteria
- Local run from reference PDF to PPTX completes with deterministic artifacts and passing QA.
- Every slide element in output can be traced to source evidence metadata.
- Hooks block invalid/unsafe flows before output generation.
- MCP endpoints stay minimal, typed, and bounded to required operations.
