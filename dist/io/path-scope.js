"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolvePathInScope = void 0;
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const errors_1 = require("./errors");
const hasParentTraversal = (value) => {
    for (const part of value.split(/[\\/]+/)) {
        if (part === '..') {
            return true;
        }
    }
    return false;
};
const isInScope = (root, candidate) => {
    if (candidate === root) {
        return true;
    }
    const rel = (0, node_path_1.relative)(root, candidate);
    return rel.length > 0 && !rel.startsWith('..') && !(0, node_path_1.isAbsolute)(rel);
};
const getNearestExistingAncestor = (targetPath) => {
    let currentPath = targetPath;
    while (!(0, node_fs_1.existsSync)(currentPath)) {
        const parentPath = (0, node_path_1.dirname)(currentPath);
        if (parentPath === currentPath) {
            break;
        }
        currentPath = parentPath;
    }
    return currentPath;
};
const assertNoSymlink = (targetPath, kind) => {
    if (!(0, node_fs_1.existsSync)(targetPath)) {
        return;
    }
    if ((0, node_fs_1.lstatSync)(targetPath).isSymbolicLink()) {
        throw new errors_1.IoContractError('PATH_OUT_OF_SCOPE', `PATH_OUT_OF_SCOPE: ${kind} path cannot be a symbolic link (${targetPath})`);
    }
};
const resolvePathInScope = ({ kind, projectRoot = process.cwd(), userPath, }) => {
    const rootRealPath = (0, node_fs_1.realpathSync)(projectRoot);
    if (hasParentTraversal(userPath)) {
        throw new errors_1.IoContractError('PATH_OUT_OF_SCOPE', `PATH_OUT_OF_SCOPE: ${kind} path contains parent traversal (${userPath})`);
    }
    const resolvedPath = (0, node_path_1.isAbsolute)(userPath) ? (0, node_path_1.resolve)(userPath) : (0, node_path_1.resolve)(rootRealPath, userPath);
    if (!isInScope(rootRealPath, resolvedPath)) {
        throw new errors_1.IoContractError('PATH_OUT_OF_SCOPE', `PATH_OUT_OF_SCOPE: ${kind} path resolves outside project root (${userPath})`);
    }
    const existingAncestor = getNearestExistingAncestor(resolvedPath);
    const ancestorRealPath = (0, node_fs_1.realpathSync)(existingAncestor);
    if (!isInScope(rootRealPath, ancestorRealPath)) {
        throw new errors_1.IoContractError('PATH_OUT_OF_SCOPE', `PATH_OUT_OF_SCOPE: ${kind} path escapes project root via symlink (${userPath})`);
    }
    const scopeRoot = `${rootRealPath}${node_path_1.sep}`;
    const scopeAncestor = `${ancestorRealPath}${node_path_1.sep}`;
    if (!scopeAncestor.startsWith(scopeRoot) && ancestorRealPath !== rootRealPath) {
        throw new errors_1.IoContractError('PATH_OUT_OF_SCOPE', `PATH_OUT_OF_SCOPE: ${kind} path escapes project root via symlink (${userPath})`);
    }
    assertNoSymlink(resolvedPath, kind);
    return resolvedPath;
};
exports.resolvePathInScope = resolvePathInScope;
