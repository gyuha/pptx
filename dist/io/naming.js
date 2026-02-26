"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createDeterministicOutputPaths = void 0;
const node_crypto_1 = require("node:crypto");
const node_path_1 = require("node:path");
const path_scope_1 = require("./path-scope");
const hashInputFingerprint = (sourceFiles) => {
    const hash = (0, node_crypto_1.createHash)('sha256');
    for (const file of sourceFiles) {
        hash.update(file.relativePath);
        hash.update('\0');
        hash.update(file.contentHash);
        hash.update('\0');
    }
    return hash.digest('hex');
};
const createDeterministicOutputPaths = ({ outputPath, projectRoot, sourceFiles, }) => {
    const outputRootPath = (0, path_scope_1.resolvePathInScope)({ kind: 'output', projectRoot, userPath: outputPath });
    const fullHash = hashInputFingerprint(sourceFiles);
    const stem = `proposal-${fullHash.slice(0, 16)}`;
    return {
        manifestFile: (0, node_path_1.join)(outputRootPath, `${stem}.json`),
        outputFile: (0, node_path_1.join)(outputRootPath, `${stem}.pptx`),
        stem,
    };
};
exports.createDeterministicOutputPaths = createDeterministicOutputPaths;
