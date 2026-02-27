export type TemplateErrorCode = 'TEMPLATE_NOT_FOUND';

export class TemplateConfigError extends Error {
  readonly code: TemplateErrorCode;

  constructor(code: TemplateErrorCode, message: string) {
    super(message);
    this.name = 'TemplateConfigError';
    this.code = code;
  }
}

export interface RuntimeConfig {
  readonly inputPath: string;
  readonly outputPath: string;
  readonly templatePath: string;
}

const DEFAULT_TEMPLATE_PATH = 'input/template.pptx';

export interface ResolveRuntimeConfigParams {
  readonly cliInputPath?: string;
  readonly cliOutputPath?: string;
  readonly cliTemplatePath?: string;
  readonly envTemplatePath?: string | undefined;
  readonly projectRoot?: string;
}

export const resolveRuntimeConfig = ({
  cliInputPath,
  cliOutputPath,
  cliTemplatePath,
  envTemplatePath,
  projectRoot,
}: ResolveRuntimeConfigParams): RuntimeConfig => {
  if (!cliInputPath) {
    throw new TemplateConfigError(
      'TEMPLATE_NOT_FOUND',
      'TEMPLATE_NOT_FOUND: --input is required'
    );
  }

  const inputPath = cliInputPath;
  const outputPath = cliOutputPath ?? 'output';

  // Template precedence: CLI arg > env var > default
  const templatePath =
    cliTemplatePath ?? envTemplatePath ?? DEFAULT_TEMPLATE_PATH;

  return {
    inputPath,
    outputPath,
    templatePath,
  };
};
