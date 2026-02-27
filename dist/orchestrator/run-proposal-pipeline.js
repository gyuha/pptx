"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.runProposalPipeline = void 0;
const fs_1 = require("fs");
const runtime_config_1 = require("../config/runtime-config");
const discovery_1 = require("../io/discovery");
const naming_1 = require("../io/naming");
const manifest_1 = require("../io/manifest");
const markitdown_adapter_1 = require("../parsers/markitdown-adapter");
const to_proposal_model_1 = require("../normalize/to-proposal-model");
const pptx_renderer_1 = require("../render/pptx-renderer");
const resolve_template_1 = require("../template/resolve-template");
const runProposalPipeline = async ({ cliInputPath, cliOutputPath, cliTemplatePath, envTemplatePath, projectRoot, }) => {
    // Step 1: Resolve runtime configuration
    const config = (0, runtime_config_1.resolveRuntimeConfig)({
        cliInputPath,
        cliOutputPath,
        cliTemplatePath,
        envTemplatePath,
        projectRoot,
    });
    // Step 2: Discover input files
    const sourceFiles = (0, discovery_1.discoverInputFiles)({
        inputPath: config.inputPath,
        projectRoot,
    });
    // Step 3: Parse documents with MarkItDown
    const parsedDocuments = (0, markitdown_adapter_1.parseDiscoveredInputFiles)({
        sourceFiles,
    });
    // Step 4: Normalize to ProposalModel
    const model = (0, to_proposal_model_1.normalizeToProposalModel)({
        parsedDocuments,
    });
    // Step 5: Resolve template
    const resolvedTemplate = (0, resolve_template_1.resolveTemplate)(config, projectRoot);
    // Step 6: Determine output paths
    const outputPaths = (0, naming_1.createDeterministicOutputPaths)({
        outputPath: config.outputPath,
        projectRoot,
        sourceFiles,
    });
    // Step 7: Render PPTX
    const renderManifest = await (0, pptx_renderer_1.renderProposalToPptx)({
        model,
        outputPath: outputPaths.outputFile,
        templateHash: resolvedTemplate.templateHash,
    });
    // Step 8: Write manifest file
    const manifestMetadata = (0, manifest_1.buildManifestMetadata)({
        modelHash: renderManifest.modelHash,
        sourceFiles,
        templateHash: renderManifest.templateHash,
        timestamp: renderManifest.timestamp,
    });
    const manifestDir = projectRoot
        ? `${projectRoot}/${outputPaths.manifestFile.replace(/\/[^/]+$/, '')}`
        : outputPaths.manifestFile.replace(/\/[^/]+$/, '');
    await fs_1.promises.mkdir(manifestDir, { recursive: true });
    const fullManifestPath = projectRoot
        ? `${projectRoot}/${outputPaths.manifestFile}`
        : outputPaths.manifestFile;
    await fs_1.promises.writeFile(fullManifestPath, JSON.stringify(manifestMetadata, null, 2), 'utf-8');
    return {
        manifestPath: outputPaths.manifestFile,
        model,
        pptxPath: outputPaths.outputFile,
        slideCount: renderManifest.slideCount,
    };
};
exports.runProposalPipeline = runProposalPipeline;
