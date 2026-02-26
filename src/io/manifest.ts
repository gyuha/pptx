import type { DiscoveredInputFile } from './discovery';

export interface ProposalRunManifestMetadata {
  modelHash: string;
  sourceFiles: string[];
  templateHash: string;
  timestamp: string;
}

interface BuildManifestMetadataParams {
  modelHash: string;
  sourceFiles: ReadonlyArray<DiscoveredInputFile>;
  templateHash: string;
  timestamp?: string;
}

export const buildManifestMetadata = ({
  modelHash,
  sourceFiles,
  templateHash,
  timestamp = new Date().toISOString(),
}: BuildManifestMetadataParams): ProposalRunManifestMetadata => ({
  modelHash,
  sourceFiles: sourceFiles.map((file) => file.relativePath),
  templateHash,
  timestamp,
});
