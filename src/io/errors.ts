export type IoErrorCode = 'PATH_OUT_OF_SCOPE' | 'UNSUPPORTED_INPUT_EXTENSION' | 'INPUT_DIR_NOT_FOUND';

export class IoContractError extends Error {
  readonly code: IoErrorCode;

  constructor(code: IoErrorCode, message: string) {
    super(message);
    this.name = 'IoContractError';
    this.code = code;
  }
}
