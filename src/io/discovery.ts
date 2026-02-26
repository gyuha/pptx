import { createHash } from 'node:crypto';
import { lstatSync, readdirSync, readFileSync } from 'node:fs';
import { extname, join, relative } from 'node:path';

import { IoContractError } from './errors';
import { resolvePathInScope } from './path-scope';

const SUPPORTED_EXTENSIONS = new Set(['.pdf', '.docx']);

export interface DiscoveredInputFile {
  absolutePath: string;
  contentHash: string;
  extension: '.pdf' | '.docx';
  relativePath: string;
}

const normalizeRelativePath = (from: string, to: string): string =>
  relative(from, to).split('\\').join('/');

const hashFileContent = (filePath: string): string =>
  createHash('sha256').update(readFileSync(filePath)).digest('hex');

const compareByRelativePath = (a: DiscoveredInputFile, b: DiscoveredInputFile): number => {
  if (a.relativePath === b.relativePath) {
    return 0;
  }

  return a.relativePath < b.relativePath ? -1 : 1;
};

const walkInputTree = (inputRootPath: string): string[] => {
  const discoveredPaths: string[] = [];
  const pendingDirs = [inputRootPath];

  while (pendingDirs.length > 0) {
    const currentDir = pendingDirs.pop();
    if (!currentDir) {
      continue;
    }

    const childEntries = readdirSync(currentDir, { withFileTypes: true })
      .map((entry) => entry.name)
      .sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));

    for (const childName of childEntries) {
      const childPath = join(currentDir, childName);
      const stats = lstatSync(childPath);

      if (stats.isSymbolicLink()) {
        throw new IoContractError(
          'PATH_OUT_OF_SCOPE',
          `PATH_OUT_OF_SCOPE: symbolic links are not allowed in input tree (${childPath})`
        );
      }

      if (stats.isDirectory()) {
        pendingDirs.push(childPath);
        continue;
      }

      if (stats.isFile()) {
        discoveredPaths.push(childPath);
      }
    }
  }

  return discoveredPaths;
};

interface DiscoverInputFilesParams {
  inputPath: string;
  projectRoot?: string;
}

export const discoverInputFiles = ({
  inputPath,
  projectRoot,
}: DiscoverInputFilesParams): DiscoveredInputFile[] => {
  const inputRootPath = resolvePathInScope({ kind: 'input', projectRoot, userPath: inputPath });
  const rootStats = lstatSync(inputRootPath, { throwIfNoEntry: false });
  if (!rootStats || !rootStats.isDirectory()) {
    throw new IoContractError(
      'INPUT_DIR_NOT_FOUND',
      `INPUT_DIR_NOT_FOUND: input directory does not exist (${inputPath})`
    );
  }

  const sourceFiles = walkInputTree(inputRootPath).map((absolutePath) => {
    const extension = extname(absolutePath).toLowerCase();
    if (!SUPPORTED_EXTENSIONS.has(extension)) {
      throw new IoContractError(
        'UNSUPPORTED_INPUT_EXTENSION',
        `UNSUPPORTED_INPUT_EXTENSION: unsupported file type "${extension || '<none>'}" at ${absolutePath}`
      );
    }

    const typedExtension = extension as '.pdf' | '.docx';
    return {
      absolutePath,
      contentHash: hashFileContent(absolutePath),
      extension: typedExtension,
      relativePath: normalizeRelativePath(inputRootPath, absolutePath),
    };
  });

  return sourceFiles.sort(compareByRelativePath);
};
