import { basename } from 'node:path';
import { spawnSync } from 'node:child_process';
import { statSync } from 'node:fs';

import type { DiscoveredInputFile } from '../io/discovery';
import { ParserContractError } from './errors';

const DEFAULT_MAX_INPUT_BYTES = 15 * 1024 * 1024;

export interface ParsedInputDocument {
  markdown: string;
  sourceFile: string;
}

interface ParseWithMarkItDownParams {
  inputFilePath: string;
  maxInputBytes?: number;
  sourceFile?: string;
}

interface ParseDiscoveredInputFilesParams {
  maxInputBytes?: number;
  sourceFiles: ReadonlyArray<DiscoveredInputFile>;
}

interface MarkItDownFailureDiagnostic {
  errorMessage: string;
  errorType: string;
}

interface MarkItDownSuccessResult {
  markdown: string;
  ok: true;
}

interface MarkItDownFailureResult {
  diagnostic: MarkItDownFailureDiagnostic;
  ok: false;
}

type MarkItDownResult = MarkItDownSuccessResult | MarkItDownFailureResult;

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

const getSourceFileName = (inputFilePath: string, sourceFile?: string): string =>
  sourceFile ? sourceFile : basename(inputFilePath);

const assertInputSize = (inputFilePath: string, sourceFile: string, maxInputBytes: number): void => {
  const fileSize = statSync(inputFilePath).size;

  if (fileSize > maxInputBytes) {
    throw new ParserContractError(
      'INPUT_TOO_LARGE',
      sourceFile,
      `INPUT_TOO_LARGE: input file "${sourceFile}" is ${fileSize} bytes, exceeding limit ${maxInputBytes} bytes`
    );
  }
};

const parseMarkItDownResult = (
  rawStdout: string,
  rawStderr: string,
  sourceFile: string
): MarkItDownResult => {
  const normalizedStdout = rawStdout.trim();

  if (!normalizedStdout) {
    const normalizedStderr = rawStderr.trim();
    const details = normalizedStderr ? ` (${normalizedStderr})` : '';
    throw new ParserContractError(
      'PARSE_FAILED',
      sourceFile,
      `PARSE_FAILED: markitdown returned empty diagnostics for "${sourceFile}"${details}`
    );
  }

  try {
    return JSON.parse(normalizedStdout) as MarkItDownResult;
  } catch {
    throw new ParserContractError(
      'PARSE_FAILED',
      sourceFile,
      `PARSE_FAILED: unable to parse markitdown diagnostics for "${sourceFile}"`
    );
  }
};

const isEncryptedPdfDiagnostic = (diagnostic: MarkItDownFailureDiagnostic): boolean => {
  const combined = `${diagnostic.errorType} ${diagnostic.errorMessage}`.toLowerCase();
  return (
    combined.includes('pdfpasswordincorrect') ||
    combined.includes('password') ||
    combined.includes('encrypted')
  );
};

const throwNormalizedParseFailure = (
  sourceFile: string,
  diagnostic: MarkItDownFailureDiagnostic
): never => {
  if (isEncryptedPdfDiagnostic(diagnostic)) {
    throw new ParserContractError(
      'PARSE_UNSUPPORTED_ENCRYPTED',
      sourceFile,
      `PARSE_UNSUPPORTED_ENCRYPTED: encrypted or password-protected PDF is not supported for "${sourceFile}"`
    );
  }

  throw new ParserContractError(
    'PARSE_FAILED',
    sourceFile,
    `PARSE_FAILED: MarkItDown failed for "${sourceFile}" (${diagnostic.errorType}: ${diagnostic.errorMessage || '<empty>'})`
  );
};

export const parseWithMarkItDown = ({
  inputFilePath,
  maxInputBytes = DEFAULT_MAX_INPUT_BYTES,
  sourceFile,
}: ParseWithMarkItDownParams): ParsedInputDocument => {
  const sourceFileName = getSourceFileName(inputFilePath, sourceFile);

  assertInputSize(inputFilePath, sourceFileName, maxInputBytes);

  const result = spawnSync('python3', ['-c', MARKITDOWN_INLINE_SCRIPT, inputFilePath], {
    encoding: 'utf8',
  });

  if (result.error) {
    throw new ParserContractError(
      'PARSE_FAILED',
      sourceFileName,
      `PARSE_FAILED: failed to execute markitdown runtime for "${sourceFileName}" (${result.error.message})`
    );
  }

  const parsedResult = parseMarkItDownResult(result.stdout, result.stderr, sourceFileName);

  if (parsedResult.ok !== true) {
    throwNormalizedParseFailure(sourceFileName, parsedResult.diagnostic);
  }

  const markdown = (parsedResult as MarkItDownSuccessResult).markdown.trim();
  if (!markdown) {
    throw new ParserContractError(
      'PARSE_FAILED',
      sourceFileName,
      `PARSE_FAILED: MarkItDown produced empty markdown for "${sourceFileName}"`
    );
  }

  return {
    markdown,
    sourceFile: sourceFileName,
  };
};

export const parseDiscoveredInputFiles = ({
  maxInputBytes,
  sourceFiles,
}: ParseDiscoveredInputFilesParams): ParsedInputDocument[] =>
  sourceFiles.map((file) =>
    parseWithMarkItDown({
      inputFilePath: file.absolutePath,
      maxInputBytes,
      sourceFile: file.relativePath,
    })
  );
