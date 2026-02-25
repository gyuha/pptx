# RPF to Proposal PPTX Automation

## TL;DR
> **Summary**: Build a greenfield automation project that reads PDF/DOCX RPF files from `input/`, converts them into a normalized proposal model, and generates company-branded PPTX files into `output/` when triggered by a dedicated OpenCode slash command.
> **Deliverables**:
> - End-to-end CLI/command pipeline (`input/` -> parsing -> model -> `output/*.pptx`)
> - Company template application with default path and `--template` override
> - Installed and documented skill/MCP setup policy for PPTX workflows
> - Tests-after suite, deterministic output rules, and CI checks
> **Effort**: Medium
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 -> Task 3 -> Task 5 -> Task 6 -> Task 8 -> Task 9 -> Task 10

## Context
### Original Request
- `input` 폴더에 RPF 문서를 모아두고 OpenCode에서 "제작해줘"를 실행하면 `output` 폴더에 제안서 PPTX를 자동 생성하는 프로젝트 구축.
- 제공된 한국어 가이드 기준으로 필요한 스킬/MCP를 설치해 안정적으로 PPTX 제작.

### Interview Summary
- Input format: PDF + DOCX 동시 지원.
- Output quality: 회사 템플릿 적용(브랜딩 포함).
- Trigger: 전용 slash 명령.
- Template resolution: 기본 경로 + `--template` 인자 override 둘 다 지원.
- Test strategy: tests-after.

### Metis Review (gaps addressed)
- Scope locked to v1 local-file pipeline only (no remote URL ingestion, no OCR 확장).
- Template handling defined as declarative renderer-first approach with deterministic resolution precedence.
- Deterministic naming, collision policy, and manifest integrity checks included.
- Optional MCP activation guarded by security policy (disabled by default).

## Work Objectives
### Core Objective
- Agent-only executable pipeline for proposal generation: `input/*.pdf|*.docx` -> normalized proposal data -> branded `.pptx` + sidecar manifest in `output/`.

### Deliverables
- Project scaffold (Node.js + TypeScript) with build/test/lint/typecheck scripts.
- Parsing adapters using MarkItDown.
- Proposal domain model and validation.
- PPTX renderer using PptxGenJS with company branding config.
- Command integration for dedicated slash trigger (`제작해줘`) and CLI path.
- Skills/MCP installation guide and runtime guardrails.
- CI workflow and evidence artifacts under `.sisyphus/evidence/`.

### Definition of Done (verifiable conditions with commands)
- `npm run build` exits 0.
- `npm run typecheck` exits 0.
- `npm test` exits 0.
- `npm run proposal:make -- --input ./fixtures/input --output ./tmp/output` creates exactly one `.pptx` and one `.json` manifest per processing unit.
- Re-running with unchanged input produces identical manifest `modelHash` and stable output filename stem.

### Must Have
- Deterministic file ordering and naming.
- Multi-file contract: merge all supported files in `input/` into a single proposal model and output one PPTX per run.
- Template precedence: `--template` > env default > `input/template.pptx` (fallback path) or configured default style spec.
- Clear failure messages for malformed input, missing template, parser errors.
- Version-pinned dependencies and documented skill/MCP choices.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No remote URL fetching in v1.
- No OCR/image-based document extraction in v1.
- No manual PowerPoint editing as acceptance criteria.
- No unauthenticated MCP exposure beyond localhost.
- No vague "looks good" verification; all checks must be machine-verifiable.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after with Vitest.
- QA policy: every task includes happy + failure scenario.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. Shared dependencies extracted into Wave 1.

Wave 1: Foundation and contracts (Tasks 1-4)
Wave 2: Parsing/templating/rendering core (Tasks 5-8)
Wave 3: Command integration, tests, CI hardening (Tasks 9-10)

### Dependency Matrix (full, all tasks)
- Task 1 -> blocks Tasks 2, 3, 4, 5, 7, 10
- Task 2 -> blocks Task 9, Task 10
- Task 3 -> blocks Tasks 6, 8, 10
- Task 4 -> blocks Tasks 5, 6, 9
- Task 5 -> blocks Task 6
- Task 6 -> blocks Task 8
- Task 7 -> blocks Task 8
- Task 8 -> blocks Task 9, Task 10
- Task 9 -> blocks Task 10
- Task 10 -> terminal implementation gate

### Agent Dispatch Summary (wave -> task count -> categories)
- Wave 1 -> 4 tasks -> quick, unspecified-low
- Wave 2 -> 4 tasks -> deep, unspecified-high
- Wave 3 -> 2 tasks -> unspecified-high, writing

## TODOs
> Implementation + Test = ONE task. Never separate.
> Every task includes Agent Profile, Parallelization, and QA Scenarios.

- [ ] 1. Bootstrap Node+TypeScript Project Skeleton

  **What to do**: Initialize `package.json`, `tsconfig.json`, `vitest.config.ts`, base directories (`src`, `fixtures`, `input`, `output`, `.sisyphus/evidence`), and scripts (`build`, `typecheck`, `test`, `proposal:make`).
  **Must NOT do**: Add framework/UI/server components unrelated to local CLI pipeline.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: deterministic scaffold and config creation.
  - Skills: [`typescript`] - enforce strict TS conventions.
  - Omitted: [`react`] - no frontend scope.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,3,4,5,7,10 | Blocked By: none

  **References**:
  - Pattern: `README.md:1` - current repo baseline (greenfield).
  - External: `https://github.com/anthropics/skills/tree/main/skills/pptx` - pipeline expectations for PPTX tasks.

  **Acceptance Criteria**:
  - [ ] `npm run build` exits 0.
  - [ ] `npm run typecheck` exits 0.
  - [ ] `npm test` exits 0 with at least one smoke test file discovered.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path scaffold works
    Tool: interactive_bash
    Steps: npm install; npm run build; npm run typecheck; npm test
    Expected: all commands exit 0
    Evidence: .sisyphus/evidence/task-1-bootstrap.log

  Scenario: Failure on missing script key
    Tool: interactive_bash
    Steps: npm run proposal:make -- --help before command implementation
    Expected: exits non-zero with "command not implemented" or equivalent explicit message
    Evidence: .sisyphus/evidence/task-1-bootstrap-error.log
  ```

  **Commit**: YES | Message: `chore(scaffold): initialize ts project and base scripts` | Files: `package.json`, `tsconfig.json`, `vitest.config.ts`, `src/**`, `fixtures/**`

- [ ] 2. Install and Document Skills/MCP Policy

  **What to do**: Add project docs and setup scripts for official `pdf/docx/pptx` skill usage; define optional `markitdown-mcp` enablement policy (default disabled) with localhost-only guidance.
  **Must NOT do**: Auto-enable network-exposed MCP servers.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: policy and reproducible setup docs.
  - Skills: [`add-provider-doc`] - structure install and env guidance.
  - Omitted: [`build-fix`] - no compile-time focus.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 9,10 | Blocked By: 1

  **References**:
  - External: `https://raw.githubusercontent.com/johunsang/vive-md/main/vibe-coding/resources/Awesome-Claude-Skills-%ED%95%9C%EA%B5%AD%EC%96%B4-%EA%B0%80%EC%9D%B4%EB%93%9C.md` - requested source guide.
  - External: `https://github.com/anthropics/skills/tree/main/skills/pptx` - official PPTX skill.
  - External: `https://github.com/microsoft/markitdown` - parser dependency and MCP package source.

  **Acceptance Criteria**:
  - [ ] `docs/skills-mcp-setup.md` exists with install commands, version pinning, and security guardrails.
  - [ ] `npm run proposal:doctor` (or equivalent) validates required local tools and exits 0 when configured.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path setup validation
    Tool: interactive_bash
    Steps: run setup steps from docs/skills-mcp-setup.md; execute npm run proposal:doctor
    Expected: exits 0 and lists required tools as available
    Evidence: .sisyphus/evidence/task-2-skills-setup.log

  Scenario: Failure when optional MCP is misconfigured
    Tool: interactive_bash
    Steps: set invalid MCP command path; run npm run proposal:doctor
    Expected: exits non-zero with explicit remediation text
    Evidence: .sisyphus/evidence/task-2-skills-setup-error.log
  ```

  **Commit**: YES | Message: `docs(setup): add skills and mcp installation policy` | Files: `docs/skills-mcp-setup.md`, `scripts/proposal-doctor.*`

- [ ] 3. Define Proposal Domain Model and Validation Contracts

  **What to do**: Create typed schema for normalized proposal data (`ProposalModel`) and runtime validation for required sections (title, agenda, value proposition, execution plan, budget/timeline placeholders).
  **Must NOT do**: Encode company-specific confidential content in defaults.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: core contract design.
  - Skills: [`typescript`] - strict types + runtime schema alignment.
  - Omitted: [`frontend-ui-ux`] - not visual implementation.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 6,8,10 | Blocked By: 1

  **References**:
  - Pattern: `src/domain/proposal-model.ts` (new) - canonical type location.
  - External: `https://github.com/microsoft/markitdown` - markdown extraction structure to normalize.

  **Acceptance Criteria**:
  - [ ] `npm test -- proposal-model` exits 0.
  - [ ] Invalid model fixture fails validation with deterministic error code/message.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path valid model
    Tool: interactive_bash
    Steps: npm test -- proposal-model --runInBand
    Expected: valid fixture passes and emits normalized JSON snapshot
    Evidence: .sisyphus/evidence/task-3-model.log

  Scenario: Failure on missing required section
    Tool: interactive_bash
    Steps: run validator against fixture missing "valueProposition"
    Expected: exits non-zero with field-level validation error
    Evidence: .sisyphus/evidence/task-3-model-error.log
  ```

  **Commit**: YES | Message: `feat(domain): add proposal model schema and validator` | Files: `src/domain/**`, `fixtures/model/**`, `tests/domain/**`

- [ ] 4. Implement Input Discovery and Deterministic Output Naming

  **What to do**: Implement scanner for `input/` supporting `.pdf`/`.docx`, stable sort order, collision-safe naming (content hash stem), and sidecar manifest metadata.
  **Must NOT do**: Process unsupported file types silently.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: deterministic file system utility logic.
  - Skills: [`typescript`] - predictable IO and typing.
  - Omitted: [`desktop`] - no desktop runtime.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 5,6,9 | Blocked By: 1

  **References**:
  - Pattern: `src/io/discovery.ts` (new) - input enumeration.
  - Pattern: `src/io/naming.ts` (new) - output stem/hash rules.
  - External: `https://github.com/microsoft/markitdown` - supported format assumptions.

  **Acceptance Criteria**:
  - [ ] For same input set, two runs produce identical ordered file list.
  - [ ] Input contract merges all discovered files into one deterministic processing batch.
  - [ ] Manifest contains `sourceFiles`, `modelHash`, `templateHash`, and timestamp.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path deterministic ordering
    Tool: interactive_bash
    Steps: run discovery twice on fixtures/input-mixed; compare JSON outputs
    Expected: byte-identical ordering output
    Evidence: .sisyphus/evidence/task-4-discovery.log

  Scenario: Failure on unsupported extension
    Tool: interactive_bash
    Steps: add fixtures/input/bad.txt; run discovery
    Expected: exits non-zero with "unsupported file type" error
    Evidence: .sisyphus/evidence/task-4-discovery-error.log
  ```

  **Commit**: YES | Message: `feat(io): add deterministic input discovery and naming` | Files: `src/io/**`, `tests/io/**`, `fixtures/input-mixed/**`

- [ ] 5. Implement PDF/DOCX Parsing Adapters via MarkItDown

  **What to do**: Build adapter layer that invokes MarkItDown for each supported input, captures markdown/text output, and normalizes parser diagnostics.
  **Must NOT do**: Depend on MCP transport as default execution path.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: third-party integration + error normalization.
  - Skills: [`python-expert`] - if MarkItDown Python invocation wrapper is used.
  - Omitted: [`playwright`] - non-browser task.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 6 | Blocked By: 1,4

  **References**:
  - Pattern: `src/parsers/markitdown-adapter.ts` (new).
  - External: `https://github.com/microsoft/markitdown` - supported input conversion behavior.
  - External: `https://github.com/microsoft/markitdown/tree/main/packages/markitdown-mcp` - optional MCP constraints.

  **Acceptance Criteria**:
  - [ ] PDF and DOCX fixtures each produce non-empty markdown payload.
  - [ ] Parser failures include input filename and standardized error code.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path dual-format parse
    Tool: interactive_bash
    Steps: npm run test -- parser-adapter; run parse command on fixtures/input/sample.pdf and sample.docx
    Expected: both inputs produce markdown artifacts > 0 bytes
    Evidence: .sisyphus/evidence/task-5-parser.log

  Scenario: Failure on corrupt file
    Tool: interactive_bash
    Steps: parse fixtures/input/corrupt.pdf
    Expected: exits non-zero with code PARSE_FAILED and source filename
    Evidence: .sisyphus/evidence/task-5-parser-error.log
  ```

  **Commit**: YES | Message: `feat(parser): add markitdown adapters for pdf and docx` | Files: `src/parsers/**`, `tests/parsers/**`, `fixtures/input/**`

- [ ] 6. Build Normalization Pipeline to ProposalModel

  **What to do**: Transform parsed markdown/text into `ProposalModel` sections using deterministic mapping rules and fallback placeholders for missing content.
  **Must NOT do**: Introduce non-deterministic LLM calls in v1 normalization.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: domain transformation logic.
  - Skills: [`typescript`] - type-safe transformation contracts.
  - Omitted: [`research`] - no web research required during execution.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 8 | Blocked By: 3,4,5

  **References**:
  - Pattern: `src/normalize/to-proposal-model.ts` (new).
  - API/Type: `src/domain/proposal-model.ts` (from Task 3).

  **Acceptance Criteria**:
  - [ ] Given fixed fixtures, output model JSON snapshot is stable across reruns.
  - [ ] Missing sections are filled with explicit placeholders, not empty strings.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path normalized model generation
    Tool: interactive_bash
    Steps: run normalization on parsed fixture outputs; compare to approved snapshot
    Expected: snapshot match and all required sections present
    Evidence: .sisyphus/evidence/task-6-normalize.log

  Scenario: Failure on empty parse payload
    Tool: interactive_bash
    Steps: feed empty markdown to normalizer
    Expected: exits non-zero with NORMALIZATION_EMPTY_INPUT
    Evidence: .sisyphus/evidence/task-6-normalize-error.log
  ```

  **Commit**: YES | Message: `feat(normalize): map parsed content into proposal model` | Files: `src/normalize/**`, `tests/normalize/**`

- [ ] 7. Implement Company Template Resolution and Hashing

  **What to do**: Implement template lookup precedence (`--template` > env > default `input/template.pptx`), template file existence validation, and `templateHash` computation for manifest traceability.
  **Must NOT do**: Silently fallback to random defaults when specified template path is invalid.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: deterministic config/path resolution.
  - Skills: [`typescript`] - robust option parsing and typed config.
  - Omitted: [`desktop`] - no GUI required.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 8 | Blocked By: 1

  **References**:
  - Pattern: `src/template/resolve-template.ts` (new).
  - Pattern: `src/config/runtime-config.ts` (new).

  **Acceptance Criteria**:
  - [ ] CLI arg template path overrides env and default path.
  - [ ] Missing template path fails fast with actionable error.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path precedence check
    Tool: interactive_bash
    Steps: set env template; run command with --template override; inspect manifest
    Expected: manifest records override path hash, not env path hash
    Evidence: .sisyphus/evidence/task-7-template.log

  Scenario: Failure on nonexistent template path
    Tool: interactive_bash
    Steps: run command with --template ./missing/template.pptx
    Expected: exits non-zero with TEMPLATE_NOT_FOUND
    Evidence: .sisyphus/evidence/task-7-template-error.log
  ```

  **Commit**: YES | Message: `feat(template): add template precedence and hashing` | Files: `src/template/**`, `src/config/**`, `tests/template/**`

- [ ] 8. Implement PPTX Renderer with Brand Master and Manifest Output

  **What to do**: Render slide deck from `ProposalModel` using PptxGenJS masters/theme config, produce `.pptx` and `.json` manifest in `output/`, and validate PPTX zip structure.
  **Must NOT do**: Require manual slide edits to satisfy acceptance.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: core artifact generation and layout logic.
  - Skills: [`typescript`] - maintainable renderer contracts.
  - Omitted: [`frontend-ui-ux`] - presentation artifact generation is not web UI.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: 9,10 | Blocked By: 3,6,7

  **References**:
  - Pattern: `src/render/pptx-renderer.ts` (new).
  - API/Type: `src/domain/proposal-model.ts` (Task 3).
  - External: `https://github.com/anthropics/skills/tree/main/skills/pptx` - PPTX generation flow guidance.

  **Acceptance Criteria**:
  - [ ] Render command creates valid `.pptx` containing `ppt/presentation.xml` and `[Content_Types].xml`.
  - [ ] Manifest includes `modelHash`, `templateHash`, `outputFile`, and `slideCount`.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path render and structure validation
    Tool: interactive_bash
    Steps: run render command on normalized fixture; unzip -l output file
    Expected: required pptx internal entries exist and manifest fields are complete
    Evidence: .sisyphus/evidence/task-8-render.log

  Scenario: Failure on invalid model payload
    Tool: interactive_bash
    Steps: run renderer with fixture missing required section
    Expected: exits non-zero with MODEL_VALIDATION_FAILED
    Evidence: .sisyphus/evidence/task-8-render-error.log
  ```

  **Commit**: YES | Message: `feat(renderer): generate branded pptx and manifest artifacts` | Files: `src/render/**`, `tests/render/**`, `fixtures/template/**`

- [ ] 9. Add Dedicated Command Route for "제작해줘"

  **What to do**: Wire single orchestration entrypoint to both dedicated slash command route (`제작해줘`) and CLI command (`proposal:make`) so behavior is identical; support `--input`, `--output`, `--template`.
  **Must NOT do**: Duplicate business logic across slash handler and CLI.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: command router + orchestration integration.
  - Skills: [`typescript`] - command typing and option contracts.
  - Omitted: [`plan`] - execution task, not planning.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 10 | Blocked By: 2,4,8

  **References**:
  - Pattern: `src/commands/make-proposal.ts` (new).
  - Pattern: `src/cli/index.ts` (new).
  - Pattern: `src/orchestrator/run-proposal-pipeline.ts` (new).

  **Acceptance Criteria**:
  - [ ] Running slash route and CLI with same args yields identical output filenames/manifests.
  - [ ] `--help` clearly documents required/optional options and defaults.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path slash and cli parity
    Tool: interactive_bash
    Steps: execute slash route simulation; execute cli with same fixture and options; diff manifests
    Expected: no diff in output stem and manifest content except run timestamp
    Evidence: .sisyphus/evidence/task-9-command.log

  Scenario: Failure on missing input directory
    Tool: interactive_bash
    Steps: run command with --input ./missing-input
    Expected: exits non-zero with INPUT_DIR_NOT_FOUND
    Evidence: .sisyphus/evidence/task-9-command-error.log
  ```

  **Commit**: YES | Message: `feat(commands): add 제작해줘 route and shared pipeline entrypoint` | Files: `src/commands/**`, `src/cli/**`, `src/orchestrator/**`

- [ ] 10. Add Tests-After Suite, CI Workflow, and End-to-End Evidence Collection

  **What to do**: Implement tests for parser, normalization, renderer, and command parity; add CI workflow to run install/build/typecheck/test; add e2e fixture run that emits evidence logs to `.sisyphus/evidence/`.
  **Must NOT do**: Merge without CI green and artifact checks.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: cross-cutting quality gate and automation.
  - Skills: [`testing`] - robust Vitest patterns and fixture-driven tests.
  - Omitted: [`frontend-ui-ux`] - no UI design scope.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: none | Blocked By: 1,2,3,8,9

  **References**:
  - Pattern: `.github/workflows/ci.yml` (new).
  - Pattern: `tests/e2e/proposal-generation.test.ts` (new).
  - Pattern: `scripts/collect-evidence.*` (new).

  **Acceptance Criteria**:
  - [ ] CI executes build/typecheck/test and exits 0 on main workflow.
  - [ ] E2E test validates valid PPTX zip entries and manifest integrity fields.
  - [ ] Determinism check passes for two consecutive runs on same fixtures.

  **QA Scenarios**:
  ```bash
  Scenario: Happy path full pipeline in CI-equivalent mode
    Tool: interactive_bash
    Steps: npm ci; npm run build; npm run typecheck; npm test; npm run proposal:make -- --input ./fixtures/input --output ./tmp/output
    Expected: all commands exit 0 and evidence artifacts are written
    Evidence: .sisyphus/evidence/task-10-quality.log

  Scenario: Failure gate on broken fixture contract
    Tool: interactive_bash
    Steps: run e2e test with intentionally malformed fixture
    Expected: test fails with explicit contract mismatch and non-zero exit
    Evidence: .sisyphus/evidence/task-10-quality-error.log
  ```

  **Commit**: YES | Message: `test(ci): add e2e verification and automated quality gates` | Files: `tests/**`, `.github/workflows/ci.yml`, `scripts/**`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit - oracle
- [ ] F2. Code Quality Review - unspecified-high
- [ ] F3. Real Manual QA - unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check - deep

## Commit Strategy
- Commit per completed task when acceptance criteria pass.
- Conventional commits enforced: `feat(scope): ...`, `chore(scope): ...`, `test(scope): ...`, `docs(scope): ...`.
- Do not squash unrelated setup + feature + test changes into one commit.

## Success Criteria
- User can place RPF files in `input/`, run dedicated command (`제작해줘` route), and receive branded PPTX artifacts in `output/` without manual intervention.
- Pipeline failures are explicit, reproducible, and covered by automated tests.
- Skill/MCP setup is documented, reproducible, and secure-by-default.
