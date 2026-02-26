"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ParserContractError = void 0;
class ParserContractError extends Error {
    code;
    sourceFile;
    constructor(code, sourceFile, message) {
        super(message);
        this.name = 'ParserContractError';
        this.code = code;
        this.sourceFile = sourceFile;
    }
}
exports.ParserContractError = ParserContractError;
