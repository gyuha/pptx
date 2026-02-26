"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.IoContractError = void 0;
class IoContractError extends Error {
    code;
    constructor(code, message) {
        super(message);
        this.name = 'IoContractError';
        this.code = code;
    }
}
exports.IoContractError = IoContractError;
