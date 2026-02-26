import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { ParserContractError, parseWithMarkItDown } from '../../src/parsers';

const fixturePath = (name: string): string =>
  resolve(process.cwd(), 'fixtures', 'input', name);

describe('parsers/markitdown-adapter', () => {
  it('parses a valid PDF into non-empty markdown', () => {
    const result = parseWithMarkItDown({
      inputFilePath: fixturePath('valid.pdf'),
      sourceFile: 'valid.pdf',
    });

    expect(result.sourceFile).toBe('valid.pdf');
    expect(result.markdown.length).toBeGreaterThan(0);
    expect(result.markdown.toLowerCase()).toContain('hello pdf');
  });

  it('parses a valid DOCX into non-empty markdown', () => {
    const result = parseWithMarkItDown({
      inputFilePath: fixturePath('valid.docx'),
      sourceFile: 'valid.docx',
    });

    expect(result.sourceFile).toBe('valid.docx');
    expect(result.markdown.length).toBeGreaterThan(0);
    expect(result.markdown.toLowerCase()).toContain('hello docx');
  });

  it('fails with PARSE_FAILED and source filename for corrupt PDF', () => {
    const run = () =>
      parseWithMarkItDown({
        inputFilePath: fixturePath('corrupt.pdf'),
        sourceFile: 'corrupt.pdf',
      });

    expect(run).toThrow(ParserContractError);
    expect(run).toThrowError(/PARSE_FAILED/);

    try {
      run();
      throw new Error('Expected PARSE_FAILED for corrupt fixture');
    } catch (error) {
      expect(error).toBeInstanceOf(ParserContractError);
      const typedError = error as ParserContractError;
      expect(typedError.code).toBe('PARSE_FAILED');
      expect(typedError.sourceFile).toBe('corrupt.pdf');
      expect(typedError.message).toContain('corrupt.pdf');
    }
  });

  it('fails with PARSE_UNSUPPORTED_ENCRYPTED and source filename for encrypted PDF', () => {
    const run = () =>
      parseWithMarkItDown({
        inputFilePath: fixturePath('encrypted.pdf'),
        sourceFile: 'encrypted.pdf',
      });

    expect(run).toThrow(ParserContractError);
    expect(run).toThrowError(/PARSE_UNSUPPORTED_ENCRYPTED/);

    try {
      run();
      throw new Error('Expected PARSE_UNSUPPORTED_ENCRYPTED for encrypted fixture');
    } catch (error) {
      expect(error).toBeInstanceOf(ParserContractError);
      const typedError = error as ParserContractError;
      expect(typedError.code).toBe('PARSE_UNSUPPORTED_ENCRYPTED');
      expect(typedError.sourceFile).toBe('encrypted.pdf');
      expect(typedError.message).toContain('encrypted.pdf');
    }
  });

  it('fails fast with INPUT_TOO_LARGE before parse attempt', () => {
    const run = () =>
      parseWithMarkItDown({
        inputFilePath: fixturePath('valid.docx'),
        maxInputBytes: 8,
        sourceFile: 'valid.docx',
      });

    expect(run).toThrow(ParserContractError);
    expect(run).toThrowError(/INPUT_TOO_LARGE/);

    try {
      run();
      throw new Error('Expected INPUT_TOO_LARGE for oversized fixture');
    } catch (error) {
      expect(error).toBeInstanceOf(ParserContractError);
      const typedError = error as ParserContractError;
      expect(typedError.code).toBe('INPUT_TOO_LARGE');
      expect(typedError.sourceFile).toBe('valid.docx');
      expect(typedError.message).toContain('valid.docx');
    }
  });
});
