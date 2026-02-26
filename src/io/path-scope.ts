import { existsSync, lstatSync, realpathSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';

import { IoContractError } from './errors';

export type ScopedPathKind = 'input' | 'output' | 'template';

const hasParentTraversal = (value: string): boolean => {
  for (const part of value.split(/[\\/]+/)) {
    if (part === '..') {
      return true;
    }
  }

  return false;
};

const isInScope = (root: string, candidate: string): boolean => {
  if (candidate === root) {
    return true;
  }

  const rel = relative(root, candidate);
  return rel.length > 0 && !rel.startsWith('..') && !isAbsolute(rel);
};

const getNearestExistingAncestor = (targetPath: string): string => {
  let currentPath = targetPath;

  while (!existsSync(currentPath)) {
    const parentPath = dirname(currentPath);
    if (parentPath === currentPath) {
      break;
    }

    currentPath = parentPath;
  }

  return currentPath;
};

const assertNoSymlink = (targetPath: string, kind: ScopedPathKind): void => {
  if (!existsSync(targetPath)) {
    return;
  }

  if (lstatSync(targetPath).isSymbolicLink()) {
    throw new IoContractError(
      'PATH_OUT_OF_SCOPE',
      `PATH_OUT_OF_SCOPE: ${kind} path cannot be a symbolic link (${targetPath})`
    );
  }
};

interface ResolvePathInScopeParams {
  kind: ScopedPathKind;
  projectRoot?: string;
  userPath: string;
}

export const resolvePathInScope = ({
  kind,
  projectRoot = process.cwd(),
  userPath,
}: ResolvePathInScopeParams): string => {
  const rootRealPath = realpathSync(projectRoot);

  if (hasParentTraversal(userPath)) {
    throw new IoContractError(
      'PATH_OUT_OF_SCOPE',
      `PATH_OUT_OF_SCOPE: ${kind} path contains parent traversal (${userPath})`
    );
  }

  const resolvedPath = isAbsolute(userPath) ? resolve(userPath) : resolve(rootRealPath, userPath);

  if (!isInScope(rootRealPath, resolvedPath)) {
    throw new IoContractError(
      'PATH_OUT_OF_SCOPE',
      `PATH_OUT_OF_SCOPE: ${kind} path resolves outside project root (${userPath})`
    );
  }

  const existingAncestor = getNearestExistingAncestor(resolvedPath);
  const ancestorRealPath = realpathSync(existingAncestor);

  if (!isInScope(rootRealPath, ancestorRealPath)) {
    throw new IoContractError(
      'PATH_OUT_OF_SCOPE',
      `PATH_OUT_OF_SCOPE: ${kind} path escapes project root via symlink (${userPath})`
    );
  }

  const scopeRoot = `${rootRealPath}${sep}`;
  const scopeAncestor = `${ancestorRealPath}${sep}`;
  if (!scopeAncestor.startsWith(scopeRoot) && ancestorRealPath !== rootRealPath) {
    throw new IoContractError(
      'PATH_OUT_OF_SCOPE',
      `PATH_OUT_OF_SCOPE: ${kind} path escapes project root via symlink (${userPath})`
    );
  }

  assertNoSymlink(resolvedPath, kind);

  return resolvedPath;
};
