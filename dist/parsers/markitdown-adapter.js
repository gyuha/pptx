"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseDiscoveredInputFiles = exports.parseWithMarkItDown = void 0;
const node_path_1 = require("node:path");
const node_child_process_1 = require("node:child_process");
const node_fs_1 = require("node:fs");
const errors_1 = require("./errors");
const DEFAULT_MAX_INPUT_BYTES = 15 * 1024 * 1024;
const MARKITDOWN_INLINE_SCRIPT = [
    'import json, sys',
    'from markitdown import MarkItDown',
    'path = sys.argv[1]',
    'try:',
    '  result = MarkItDown().convert(path)',
    '  text = getattr(result, "text_content", "") or ""',
    '  print(json.dumps({"ok": True, "markdown": text}))',
    'except Exception as exc:',
    '  print(json.dumps({"ok": False, "diagnostic": {"errorType": type(exc).__name__, "errorMessage": str(exc)}}))',
].join('\n');
const getSourceFileName = (inputFilePath, sourceFile) => sourceFile ? sourceFile : (0, node_path_1.basename)(inputFilePath);
const assertInputSize = (inputFilePath, sourceFile, maxInputBytes) => {
    const fileSize = (0, node_fs_1.statSync)(inputFilePath).size;
    if (fileSize > maxInputBytes) {
        throw new errors_1.ParserContractError('INPUT_TOO_LARGE', sourceFile, `INPUT_TOO_LARGE: input file "${sourceFile}" is ${fileSize} bytes, exceeding limit ${maxInputBytes} bytes`);
    }
};
const parseMarkItDownResult = (rawStdout, rawStderr, sourceFile) => {
    const normalizedStdout = rawStdout.trim();
    if (!normalizedStdout) {
        const normalizedStderr = rawStderr.trim();
        const details = normalizedStderr ? ` (${normalizedStderr})` : '';
        throw new errors_1.ParserContractError('PARSE_FAILED', sourceFile, `PARSE_FAILED: markitdown returned empty diagnostics for "${sourceFile}"${details}`);
    }
    try {
        return JSON.parse(normalizedStdout);
    }
    catch {
        throw new errors_1.ParserContractError('PARSE_FAILED', sourceFile, `PARSE_FAILED: unable to parse markitdown diagnostics for "${sourceFile}"`);
    }
};
const isEncryptedPdfDiagnostic = (diagnostic) => {
    const combined = `${diagnostic.errorType} ${diagnostic.errorMessage}`.toLowerCase();
    return (combined.includes('pdfpasswordincorrect') ||
        combined.includes('password') ||
        combined.includes('encrypted'));
};
const throwNormalizedParseFailure = (sourceFile, diagnostic) => {
    if (isEncryptedPdfDiagnostic(diagnostic)) {
        throw new errors_1.ParserContractError('PARSE_UNSUPPORTED_ENCRYPTED', sourceFile, `PARSE_UNSUPPORTED_ENCRYPTED: encrypted or password-protected PDF is not supported for "${sourceFile}"`);
    }
    throw new errors_1.ParserContractError('PARSE_FAILED', sourceFile, `PARSE_FAILED: MarkItDown failed for "${sourceFile}" (${diagnostic.errorType}: ${diagnostic.errorMessage || '<empty>'})`);
};
const parseWithMarkItDown = ({ inputFilePath, maxInputBytes = DEFAULT_MAX_INPUT_BYTES, sourceFile, }) => {
    const sourceFileName = getSourceFileName(inputFilePath, sourceFile);
    assertInputSize(inputFilePath, sourceFileName, maxInputBytes);
    const result = (0, node_child_process_1.spawnSync)('python3', ['-c', MARKITDOWN_INLINE_SCRIPT, inputFilePath], {
        encoding: 'utf8',
    });
    if (result.error) {
        throw new errors_1.ParserContractError('PARSE_FAILED', sourceFileName, `PARSE_FAILED: failed to execute markitdown runtime for "${sourceFileName}" (${result.error.message})`);
    }
    const parsedResult = parseMarkItDownResult(result.stdout, result.stderr, sourceFileName);
    if (parsedResult.ok !== true) {
        throwNormalizedParseFailure(sourceFileName, parsedResult.diagnostic);
    }
    const markdown = parsedResult.markdown.trim();
    if (!markdown) {
        throw new errors_1.ParserContractError('PARSE_FAILED', sourceFileName, `PARSE_FAILED: MarkItDown produced empty markdown for "${sourceFileName}"`);
    }
    return {
        markdown,
        sourceFile: sourceFileName,
    };
};
exports.parseWithMarkItDown = parseWithMarkItDown;
const parseDiscoveredInputFiles = ({ maxInputBytes, sourceFiles, }) => sourceFiles.map((file) => (0, exports.parseWithMarkItDown)({
    inputFilePath: file.absolutePath,
    maxInputBytes,
    sourceFile: file.relativePath,
}));
exports.parseDiscoveredInputFiles = parseDiscoveredInputFiles;
