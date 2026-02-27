import { promises as fs } from 'fs';
import { resolveRuntimeConfig } from '../config/runtime-config';
import { discoverInputFiles } from '../io/discovery';
import { createDeterministicOutputPaths } from '../io/naming';
import { buildManifestMetadata } from '../io/manifest';
import { parseDiscoveredInputFiles } from '../parsers/markitdown-adapter';
import { normalizeToProposalModel } from '../normalize/to-proposal-model';
import { renderProposalToPptx } from '../render/pptx-renderer';
import { resolveTemplate } from '../template/resolve-template';
import type { ProposalModel } from '../domain/proposal-model';

export interface PipelineResult {
  manifestPath: string;
  model: ProposalModel;
  pptxPath: string;
  slideCount: number;
}

export interface RunProposalPipelineParams {
  cliInputPath: string;
  cliOutputPath?: string;
  cliTemplatePath?: string;
  envTemplatePath?: string | undefined;
  projectRoot?: string;
}

export const runProposalPipeline = async ({
  cliInputPath,
  cliOutputPath,
  cliTemplatePath,
  envTemplatePath,
  projectRoot,
}: RunProposalPipelineParams): Promise<PipelineResult> => {
  // Step 1: Resolve runtime configuration
  const config = resolveRuntimeConfig({
    cliInputPath,
    cliOutputPath,
    cliTemplatePath,
    envTemplatePath,
    projectRoot,
  });

  // Step 2: Discover input files
  const sourceFiles = discoverInputFiles({
    inputPath: config.inputPath,
    projectRoot,
  });

  // Step 3: Parse documents with MarkItDown
  const parsedDocuments = parseDiscoveredInputFiles({
    sourceFiles,
  });

  // Step 4: Normalize to ProposalModel
  const model = normalizeToProposalModel({
    parsedDocuments,
  });

  // Step 5: Resolve template
  const resolvedTemplate = resolveTemplate(config, projectRoot);

  // Step 6: Determine output paths
  const outputPaths = createDeterministicOutputPaths({
    outputPath: config.outputPath,
    projectRoot,
    sourceFiles,
  });

  // Step 7: Render PPTX
  const renderManifest = await renderProposalToPptx({
    model,
    outputPath: outputPaths.outputFile,
    templateHash: resolvedTemplate.templateHash,
  });

  // Step 8: Write manifest file
  const manifestMetadata = buildManifestMetadata({
    modelHash: renderManifest.modelHash,
    sourceFiles,
    templateHash: renderManifest.templateHash,
    timestamp: renderManifest.timestamp,
  });

  const manifestDir = projectRoot
    ? `${projectRoot}/${outputPaths.manifestFile.replace(/\/[^/]+$/, '')}`
    : outputPaths.manifestFile.replace(/\/[^/]+$/, '');
  await fs.mkdir(manifestDir, { recursive: true });

  const fullManifestPath = projectRoot
    ? `${projectRoot}/${outputPaths.manifestFile}`
    : outputPaths.manifestFile;
  await fs.writeFile(fullManifestPath, JSON.stringify(manifestMetadata, null, 2), 'utf-8');

  return {
    manifestPath: outputPaths.manifestFile,
    model,
    pptxPath: outputPaths.outputFile,
    slideCount: renderManifest.slideCount,
  };
};
