import { mkdtempSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  createDeterministicOutputPaths,
  discoverInputFiles,
  IoContractError,
  resolvePathInScope,
} from '../../src/io';

const projectRoot = process.cwd();

describe('io/path-scope', () => {
  it('fails with PATH_OUT_OF_SCOPE for out-of-root input path and writes nothing', () => {
    const outsideRoot = mkdtempSync(resolve(tmpdir(), 'task4-outside-root-'));
    const outputRoot = mkdtempSync(resolve(tmpdir(), 'task4-outside-output-'));

    try {
      const run = () =>
        discoverInputFiles({
          inputPath: outsideRoot,
          projectRoot,
        });

      expect(run).toThrow(IoContractError);
      expect(run).toThrowError(/PATH_OUT_OF_SCOPE/);

      try {
        run();
        throw new Error('Expected PATH_OUT_OF_SCOPE');
      } catch (error) {
        expect(error).toBeInstanceOf(IoContractError);
        const typedError = error as IoContractError;
        expect(typedError.code).toBe('PATH_OUT_OF_SCOPE');
      }

      expect(readdirSync(outputRoot)).toEqual([]);
    } finally {
      rmSync(outsideRoot, { force: true, recursive: true });
      rmSync(outputRoot, { force: true, recursive: true });
    }
  });

  it('fails with PATH_OUT_OF_SCOPE for out-of-root output path and writes nothing', () => {
    const sourceFiles = discoverInputFiles({
      inputPath: resolve(projectRoot, 'fixtures', 'input-mixed'),
      projectRoot,
    });
    const outsideOutputRoot = mkdtempSync(resolve(tmpdir(), 'task4-outside-output-root-'));

    try {
      const run = () =>
        createDeterministicOutputPaths({
          outputPath: outsideOutputRoot,
          projectRoot,
          sourceFiles,
        });

      expect(run).toThrow(IoContractError);
      expect(run).toThrowError(/PATH_OUT_OF_SCOPE/);
      expect(readdirSync(outsideOutputRoot)).toEqual([]);
    } finally {
      rmSync(outsideOutputRoot, { force: true, recursive: true });
    }
  });

  it('fails with PATH_OUT_OF_SCOPE for out-of-root template path', () => {
    const outsideTemplate = mkdtempSync(resolve(tmpdir(), 'task4-outside-template-'));

    try {
      const run = () =>
        resolvePathInScope({
          kind: 'template',
          projectRoot,
          userPath: outsideTemplate,
        });

      expect(run).toThrow(IoContractError);
      expect(run).toThrowError(/PATH_OUT_OF_SCOPE/);
    } finally {
      rmSync(outsideTemplate, { force: true, recursive: true });
    }
  });

  it('fails with PATH_OUT_OF_SCOPE for parent traversal path input', () => {
    const run = () =>
      resolvePathInScope({
        kind: 'input',
        projectRoot,
        userPath: '../outside',
      });

    expect(run).toThrow(IoContractError);
    expect(run).toThrowError(/PATH_OUT_OF_SCOPE/);
  });
});
