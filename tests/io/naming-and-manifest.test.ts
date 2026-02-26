import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  buildManifestMetadata,
  createDeterministicOutputPaths,
  discoverInputFiles,
} from '../../src/io';

const projectRoot = process.cwd();

describe('io/naming-and-manifest', () => {
  it('creates deterministic output names from source content hash', () => {
    const sourceFiles = discoverInputFiles({
      inputPath: resolve(projectRoot, 'fixtures', 'input-mixed'),
      projectRoot,
    });

    const firstRun = createDeterministicOutputPaths({
      outputPath: 'output',
      projectRoot,
      sourceFiles,
    });

    const secondRun = createDeterministicOutputPaths({
      outputPath: 'output',
      projectRoot,
      sourceFiles,
    });

    expect(firstRun).toEqual(secondRun);
    expect(firstRun.stem).toMatch(/^proposal-[0-9a-f]{16}$/);
    expect(firstRun.outputFile).toContain(`${firstRun.stem}.pptx`);
    expect(firstRun.manifestFile).toContain(`${firstRun.stem}.json`);
  });

  it('includes required metadata fields in manifest payload', () => {
    const sourceFiles = discoverInputFiles({
      inputPath: resolve(projectRoot, 'fixtures', 'input-mixed'),
      projectRoot,
    });

    const manifest = buildManifestMetadata({
      modelHash: 'model-hash-001',
      sourceFiles,
      templateHash: 'template-hash-001',
      timestamp: '2026-02-25T00:00:00.000Z',
    });

    expect(manifest).toEqual({
      modelHash: 'model-hash-001',
      sourceFiles: ['a-first.pdf', 'nested/m-middle.pdf', 'z-last.docx'],
      templateHash: 'template-hash-001',
      timestamp: '2026-02-25T00:00:00.000Z',
    });
  });
});
