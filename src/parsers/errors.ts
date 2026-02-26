export type ParserErrorCode =
  | 'INPUT_TOO_LARGE'
  | 'PARSE_FAILED'
  | 'PARSE_UNSUPPORTED_ENCRYPTED';

export class ParserContractError extends Error {
  readonly code: ParserErrorCode;
  readonly sourceFile: string;

  constructor(code: ParserErrorCode, sourceFile: string, message: string) {
    super(message);
    this.name = 'ParserContractError';
    this.code = code;
    this.sourceFile = sourceFile;
  }
}
