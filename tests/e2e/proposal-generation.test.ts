import { mkdirSync, rmSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

import { discoverInputFiles } from '../../src/io';
import { parseDiscoveredInputFiles } from '../../src/parsers';
import { normalizeToProposalModel } from '../../src/normalize';

const projectRoot = process.cwd();
const tempOutputDir = resolve(projectRoot, '.tmp-e2e-output');

describe('e2e: proposal-generation', () => {
  afterEach(() => {
    try {
      rmSync(tempOutputDir, { force: true, recursive: true });
    } catch {
      // Ignore cleanup errors
    }
  });

  it('validates deterministic output across two consecutive runs on same fixtures', () => {
    const inputPath = resolve(projectRoot, 'fixtures', 'input-mixed');

    // First run
    const firstRunFiles = discoverInputFiles({ inputPath, projectRoot });
    const firstRunParsed = parseDiscoveredInputFiles({ sourceFiles: firstRunFiles });
    const firstRunModel = normalizeToProposalModel({ parsedDocuments: firstRunParsed });

    // Second run - identical input should produce identical output
    const secondRunFiles = discoverInputFiles({ inputPath, projectRoot });
    const secondRunParsed = parseDiscoveredInputFiles({ sourceFiles: secondRunFiles });
    const secondRunModel = normalizeToProposalModel({ parsedDocuments: secondRunParsed });

    // Verify determinism
    expect(firstRunFiles).toEqual(secondRunFiles);
    expect(firstRunModel).toEqual(secondRunModel);
  });

  it('validates PPTX structure and manifest integrity (pending renderer implementation)', () => {
    // This test will be enhanced once Task 8 (renderer) and Task 9 (commands) are complete
    // For now, verify the pipeline up to normalization works with valid fixtures only
    const inputPath = resolve(projectRoot, 'fixtures', 'input-mixed');

    const discoveredFiles = discoverInputFiles({ inputPath, projectRoot });
    expect(discoveredFiles.length).toBeGreaterThan(0);

    const parsedDocuments = parseDiscoveredInputFiles({ sourceFiles: discoveredFiles });
    expect(parsedDocuments.length).toBeGreaterThan(0);
    expect(parsedDocuments.every((doc) => doc.markdown.length > 0)).toBe(true);

    const model = normalizeToProposalModel({ parsedDocuments });
    expect(model.title).toBeTruthy();
    expect(model.agenda.length).toBeGreaterThan(0);
    expect(model.valueProposition).toBeTruthy();
    expect(model.executionPlan).toBeTruthy();
    expect(model.budgetTimeline.budget).toBeTruthy();
    expect(model.budgetTimeline.timeline).toBeTruthy();

    // TODO: Once renderer is implemented, verify:
    // 1. PPTX file is created with valid zip structure
    // 2. Required entries exist: ppt/presentation.xml, [Content_Types].xml
    // 3. Manifest JSON exists with modelHash, templateHash, outputFile, slideCount
  });

  it('fails gracefully on malformed input contract (pending command integration)', () => {
    // This test will be enhanced once Task 9 (commands) is complete
    // For now, verify discovery fails appropriately
    const run = () => discoverInputFiles({ inputPath: '/nonexistent/path', projectRoot });

    expect(run).toThrow();
    // PATH_OUT_OF_SCOPE is thrown before INPUT_DIR_NOT_FOUND for absolute paths outside project root
    expect(run).toThrowError(/PATH_OUT_OF_SCOPE/);

    // TODO: Once command integration is complete, verify full pipeline error handling
  });
});
