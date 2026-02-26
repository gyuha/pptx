import { cpSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { discoverInputFiles, IoContractError } from '../../src/io';

const projectRoot = process.cwd();

const withTempInputCopy = (fixtureDirName: string, run: (inputPath: string) => void): void => {
  const tempParent = resolve(projectRoot, '.tmp-tests');
  mkdirSync(tempParent, { recursive: true });
  const tempRoot = mkdtempSync(resolve(tempParent, 'task4-discovery-'));
  const inputPath = resolve(tempRoot, 'input');
  const sourceFixturePath = resolve(projectRoot, 'fixtures', fixtureDirName);

  cpSync(sourceFixturePath, inputPath, { recursive: true });

  try {
    run(inputPath);
  } finally {
    rmSync(tempRoot, { force: true, recursive: true });
  }
};

describe('io/discovery', () => {
  it('returns byte-stable deterministic ordering across reruns', () => {
    withTempInputCopy('input-mixed', (inputPath) => {
      const firstRun = discoverInputFiles({ inputPath, projectRoot });
      const secondRun = discoverInputFiles({ inputPath, projectRoot });

      const firstList = firstRun.map((file) => file.relativePath);
      const secondList = secondRun.map((file) => file.relativePath);

      expect(firstList).toEqual(secondList);
      expect(firstList).toEqual(['a-first.pdf', 'nested/m-middle.pdf', 'z-last.docx']);
    });
  });

  it('fails with explicit unsupported extension error', () => {
    withTempInputCopy('input-mixed', (inputPath) => {
      writeFileSync(resolve(inputPath, 'bad.txt'), 'unsupported text payload');

      const run = () => discoverInputFiles({ inputPath, projectRoot });

      expect(run).toThrow(IoContractError);
      expect(run).toThrowError(/UNSUPPORTED_INPUT_EXTENSION/);

      try {
        run();
        throw new Error('Expected unsupported extension to fail');
      } catch (error) {
        expect(error).toBeInstanceOf(IoContractError);
        const typedError = error as IoContractError;
        expect(typedError.code).toBe('UNSUPPORTED_INPUT_EXTENSION');
        expect(typedError.message).toMatch(/unsupported file type/i);
      }
    });
  });

  it('fails with PATH_OUT_OF_SCOPE when encountering a symlink escape in input tree', () => {
    mkdirSync(resolve(projectRoot, '.tmp-tests'), { recursive: true });
    const outsideFileRoot = mkdtempSync(resolve(projectRoot, '.tmp-tests', 'task4-symlink-outside-'));
    writeFileSync(resolve(outsideFileRoot, 'outside.pdf'), 'outside');

    try {
      withTempInputCopy('input-mixed', (inputPath) => {
        symlinkSync(resolve(outsideFileRoot, 'outside.pdf'), resolve(inputPath, 'linked.pdf'));

        const run = () => discoverInputFiles({ inputPath, projectRoot });

        expect(run).toThrow(IoContractError);
        expect(run).toThrowError(/PATH_OUT_OF_SCOPE/);
      });
    } finally {
      rmSync(outsideFileRoot, { force: true, recursive: true });
    }
  });
});
