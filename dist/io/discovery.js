"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.discoverInputFiles = void 0;
const node_crypto_1 = require("node:crypto");
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const errors_1 = require("./errors");
const path_scope_1 = require("./path-scope");
const SUPPORTED_EXTENSIONS = new Set(['.pdf', '.docx']);
const normalizeRelativePath = (from, to) => (0, node_path_1.relative)(from, to).split('\\').join('/');
const hashFileContent = (filePath) => (0, node_crypto_1.createHash)('sha256').update((0, node_fs_1.readFileSync)(filePath)).digest('hex');
const compareByRelativePath = (a, b) => {
    if (a.relativePath === b.relativePath) {
        return 0;
    }
    return a.relativePath < b.relativePath ? -1 : 1;
};
const walkInputTree = (inputRootPath) => {
    const discoveredPaths = [];
    const pendingDirs = [inputRootPath];
    while (pendingDirs.length > 0) {
        const currentDir = pendingDirs.pop();
        if (!currentDir) {
            continue;
        }
        const childEntries = (0, node_fs_1.readdirSync)(currentDir, { withFileTypes: true })
            .map((entry) => entry.name)
            .sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
        for (const childName of childEntries) {
            const childPath = (0, node_path_1.join)(currentDir, childName);
            const stats = (0, node_fs_1.lstatSync)(childPath);
            if (stats.isSymbolicLink()) {
                throw new errors_1.IoContractError('PATH_OUT_OF_SCOPE', `PATH_OUT_OF_SCOPE: symbolic links are not allowed in input tree (${childPath})`);
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
const discoverInputFiles = ({ inputPath, projectRoot, }) => {
    const inputRootPath = (0, path_scope_1.resolvePathInScope)({ kind: 'input', projectRoot, userPath: inputPath });
    const rootStats = (0, node_fs_1.lstatSync)(inputRootPath, { throwIfNoEntry: false });
    if (!rootStats || !rootStats.isDirectory()) {
        throw new errors_1.IoContractError('INPUT_DIR_NOT_FOUND', `INPUT_DIR_NOT_FOUND: input directory does not exist (${inputPath})`);
    }
    const sourceFiles = walkInputTree(inputRootPath).map((absolutePath) => {
        const extension = (0, node_path_1.extname)(absolutePath).toLowerCase();
        if (!SUPPORTED_EXTENSIONS.has(extension)) {
            throw new errors_1.IoContractError('UNSUPPORTED_INPUT_EXTENSION', `UNSUPPORTED_INPUT_EXTENSION: unsupported file type "${extension || '<none>'}" at ${absolutePath}`);
        }
        const typedExtension = extension;
        return {
            absolutePath,
            contentHash: hashFileContent(absolutePath),
            extension: typedExtension,
            relativePath: normalizeRelativePath(inputRootPath, absolutePath),
        };
    });
    return sourceFiles.sort(compareByRelativePath);
};
exports.discoverInputFiles = discoverInputFiles;
