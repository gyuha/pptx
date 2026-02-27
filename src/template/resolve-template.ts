import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';

import { IoContractError } from '../io/errors';
import { resolvePathInScope } from '../io/path-scope';
import type { RuntimeConfig } from '../config/runtime-config';
import { TemplateConfigError } from '../config/runtime-config';

export interface ResolvedTemplate {
  readonly absolutePath: string;
  readonly relativePath: string;
  readonly templateHash: string;
}

export const hashFileContent = (filePath: string): string => {
  try {
    const content = readFileSync(filePath);
    return createHash('sha256').update(content).digest('hex');
  } catch {
    throw new TemplateConfigError(
      'TEMPLATE_NOT_FOUND',
      `TEMPLATE_NOT_FOUND: cannot read template file (${filePath})`
    );
  }
};

export const resolveTemplate = (
  config: RuntimeConfig,
  projectRoot?: string
): ResolvedTemplate => {
  const resolvedPath = resolvePathInScope({
    kind: 'template',
    projectRoot,
    userPath: config.templatePath,
  });

  if (!existsSync(resolvedPath)) {
    throw new IoContractError(
      'TEMPLATE_NOT_FOUND',
      `TEMPLATE_NOT_FOUND: template file does not exist (${config.templatePath})`
    );
  }

  const templateHash = hashFileContent(resolvedPath);

  return {
    absolutePath: resolvedPath,
    relativePath: config.templatePath,
    templateHash,
  };
};
