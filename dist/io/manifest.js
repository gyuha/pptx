"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildManifestMetadata = void 0;
const buildManifestMetadata = ({ modelHash, sourceFiles, templateHash, timestamp = new Date().toISOString(), }) => ({
    modelHash,
    sourceFiles: sourceFiles.map((file) => file.relativePath),
    templateHash,
    timestamp,
});
exports.buildManifestMetadata = buildManifestMetadata;
