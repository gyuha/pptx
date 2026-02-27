"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveRuntimeConfig = exports.TemplateConfigError = void 0;
class TemplateConfigError extends Error {
    code;
    constructor(code, message) {
        super(message);
        this.name = 'TemplateConfigError';
        this.code = code;
    }
}
exports.TemplateConfigError = TemplateConfigError;
const DEFAULT_TEMPLATE_PATH = 'input/template.pptx';
const resolveRuntimeConfig = ({ cliInputPath, cliOutputPath, cliTemplatePath, envTemplatePath, projectRoot, }) => {
    if (!cliInputPath) {
        throw new TemplateConfigError('TEMPLATE_NOT_FOUND', 'TEMPLATE_NOT_FOUND: --input is required');
    }
    const inputPath = cliInputPath;
    const outputPath = cliOutputPath ?? 'output';
    // Template precedence: CLI arg > env var > default
    const templatePath = cliTemplatePath ?? envTemplatePath ?? DEFAULT_TEMPLATE_PATH;
    return {
        inputPath,
        outputPath,
        templatePath,
    };
};
exports.resolveRuntimeConfig = resolveRuntimeConfig;
