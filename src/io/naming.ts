import { createHash } from 'node:crypto';
import { join } from 'node:path';

import type { DiscoveredInputFile } from './discovery';
import { resolvePathInScope } from './path-scope';

export interface DeterministicOutputPaths {
  manifestFile: string;
  outputFile: string;
  stem: string;
}

const hashInputFingerprint = (sourceFiles: ReadonlyArray<DiscoveredInputFile>): string => {
  const hash = createHash('sha256');

  for (const file of sourceFiles) {
    hash.update(file.relativePath);
    hash.update('\0');
    hash.update(file.contentHash);
    hash.update('\0');
  }

  return hash.digest('hex');
};

interface CreateDeterministicOutputPathsParams {
  outputPath: string;
  projectRoot?: string;
  sourceFiles: ReadonlyArray<DiscoveredInputFile>;
}

export const createDeterministicOutputPaths = ({
  outputPath,
  projectRoot,
  sourceFiles,
}: CreateDeterministicOutputPathsParams): DeterministicOutputPaths => {
  const outputRootPath = resolvePathInScope({ kind: 'output', projectRoot, userPath: outputPath });
  const fullHash = hashInputFingerprint(sourceFiles);
  const stem = `proposal-${fullHash.slice(0, 16)}`;

  return {
    manifestFile: join(outputRootPath, `${stem}.json`),
    outputFile: join(outputRootPath, `${stem}.pptx`),
    stem,
  };
};
