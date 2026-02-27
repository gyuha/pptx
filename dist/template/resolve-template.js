"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveTemplate = exports.hashFileContent = void 0;
const node_crypto_1 = require("node:crypto");
const node_fs_1 = require("node:fs");
const errors_1 = require("../io/errors");
const path_scope_1 = require("../io/path-scope");
const runtime_config_1 = require("../config/runtime-config");
const hashFileContent = (filePath) => {
    try {
        const content = (0, node_fs_1.readFileSync)(filePath);
        return (0, node_crypto_1.createHash)('sha256').update(content).digest('hex');
    }
    catch {
        throw new runtime_config_1.TemplateConfigError('TEMPLATE_NOT_FOUND', `TEMPLATE_NOT_FOUND: cannot read template file (${filePath})`);
    }
};
exports.hashFileContent = hashFileContent;
const resolveTemplate = (config, projectRoot) => {
    const resolvedPath = (0, path_scope_1.resolvePathInScope)({
        kind: 'template',
        projectRoot,
        userPath: config.templatePath,
    });
    if (!(0, node_fs_1.existsSync)(resolvedPath)) {
        throw new errors_1.IoContractError('TEMPLATE_NOT_FOUND', `TEMPLATE_NOT_FOUND: template file does not exist (${config.templatePath})`);
    }
    const templateHash = (0, exports.hashFileContent)(resolvedPath);
    return {
        absolutePath: resolvedPath,
        relativePath: config.templatePath,
        templateHash,
    };
};
exports.resolveTemplate = resolveTemplate;
