import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'fs';
import path from 'path';
import { makeProposalCommand } from '../../src/commands/make-proposal';
import { runProposalPipeline } from '../../src/orchestrator/run-proposal-pipeline';
import AdmZip from 'adm-zip';

const FIXTURES_DIR = path.join(__dirname, '../fixtures/commands');
const TEMP_DIR = path.join(FIXTURES_DIR, 'temp');
const TEMPLATE_PATH = path.join(FIXTURES_DIR, 'template.pptx');

// Check if MarkItDown is available
const hasMarkItDown = () => {
  try {
    const result = require('child_process').spawnSync('python3', ['-c', 'import markitdown'], { encoding: 'utf8' });
    return result.error === undefined;
  } catch {
    return false;
  }
};

const skipIfNoMarkItDown = hasMarkItDown() ? it : it.skip;

describe('commands: make-proposal', () => {
  beforeEach(async () => {
    await fs.mkdir(TEMP_DIR, { recursive: true });
  });

  afterEach(async () => {
    await fs.rm(TEMP_DIR, { recursive: true, force: true });
  });

  describe('happy path', () => {
    skipIfNoMarkItDown('should generate proposal when called via command function', async () => {
      const inputDir = path.join(FIXTURES_DIR, 'input-valid');

      const result = await makeProposalCommand({
        input: inputDir,
        output: path.join(TEMP_DIR, 'output'),
        template: TEMPLATE_PATH,
      });

      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();

      if (result.result) {
        expect(result.result.pptxPath).toMatch(/\.pptx$/);
        expect(result.result.manifestPath).toMatch(/\.json$/);
        expect(result.result.slideCount).toBeGreaterThan(0);
        expect(result.result.model.title).toBeTruthy();

        // Verify PPTX file exists and has valid structure
        const pptxExists = await fs
          .access(result.result.pptxPath)
          .then(() => true)
          .catch(() => false);
        expect(pptxExists).toBe(true);

        const zip = new AdmZip(result.result.pptxPath);
        const entries = zip.getEntries();
        const hasPresentationXml = entries.some((e) => e.entryName.includes('ppt/presentation.xml'));
        expect(hasPresentationXml).toBe(true);
      }
    });

    skipIfNoMarkItDown('should generate identical outputs when called twice with same input', async () => {
      const inputDir = path.join(FIXTURES_DIR, 'input-valid');
      const outputDir1 = path.join(TEMP_DIR, 'output1');
      const outputDir2 = path.join(TEMP_DIR, 'output2');

      const result1 = await makeProposalCommand({
        input: inputDir,
        output: outputDir1,
        template: TEMPLATE_PATH,
      });

      const result2 = await makeProposalCommand({
        input: inputDir,
        output: outputDir2,
        template: TEMPLATE_PATH,
      });

      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);

      if (result1.result && result2.result) {
        // File stems should be identical (based on content hash)
        const stem1 = result1.result.pptxPath.split('/').pop()?.replace('.pptx', '');
        const stem2 = result2.result.pptxPath.split('/').pop()?.replace('.pptx', '');
        expect(stem1).toBe(stem2);

        // Model hashes should be identical
        const manifest1 = JSON.parse(await fs.readFile(result1.result.manifestPath, 'utf-8'));
        const manifest2 = JSON.parse(await fs.readFile(result2.result.manifestPath, 'utf-8'));
        expect(manifest1.modelHash).toBe(manifest2.modelHash);
      }
    });

    skipIfNoMarkItDown('should accept custom template path', async () => {
      const inputDir = path.join(FIXTURES_DIR, 'input-valid');
      const templatePath = path.join(FIXTURES_DIR, 'template.pptx');

      const result = await makeProposalCommand({
        input: inputDir,
        output: path.join(TEMP_DIR, 'output'),
        template: templatePath,
      });

      expect(result.success).toBe(true);
    });
  });

  describe('failure scenarios', () => {
    it('should return error for missing input directory', async () => {
      const result = await makeProposalCommand({
        input: path.join(FIXTURES_DIR, 'nonexistent'),
        output: path.join(TEMP_DIR, 'output'),
        template: TEMPLATE_PATH,
      });

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.error?.code).toBe('INPUT_DIR_NOT_FOUND');
    });

    it('should return error for nonexistent template', async () => {
      const inputDir = path.join(FIXTURES_DIR, 'input-valid');

      const result = await makeProposalCommand({
        input: inputDir,
        output: path.join(TEMP_DIR, 'output'),
        template: './nonexistent-template.pptx',
      });

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      // Either TEMPLATE_NOT_FOUND or PATH_OUT_OF_SCOPE depending on path resolution
      expect(['TEMPLATE_NOT_FOUND', 'PATH_OUT_OF_SCOPE']).toContain(result.error?.code);
    });
  });

  describe('CLI parity with orchestrator', () => {
    skipIfNoMarkItDown('should produce identical results when using orchestrator directly', async () => {
      const inputDir = path.join(FIXTURES_DIR, 'input-valid');
      const outputDir = path.join(TEMP_DIR, 'output-parity');

      const commandResult = await makeProposalCommand({
        input: inputDir,
        output: path.join(outputDir, 'command'),
        template: TEMPLATE_PATH,
      });

      const orchestratorResult = await runProposalPipeline({
        cliInputPath: inputDir,
        cliOutputPath: path.join(outputDir, 'orchestrator'),
        cliTemplatePath: TEMPLATE_PATH,
      });

      expect(commandResult.success).toBe(true);

      if (commandResult.result) {
        // Both should produce same content hash stem
        const commandStem = commandResult.result.pptxPath.split('/').pop();
        const orchestratorStem = orchestratorResult.pptxPath.split('/').pop();
        expect(commandStem).toBe(orchestratorStem);

        // Same slide count
        expect(commandResult.result.slideCount).toBe(orchestratorResult.slideCount);

        // Same model hash
        const commandManifest = JSON.parse(
          await fs.readFile(commandResult.result.manifestPath, 'utf-8')
        );
        const orchestratorManifest = JSON.parse(
          await fs.readFile(orchestratorResult.manifestPath, 'utf-8')
        );
        expect(commandManifest.modelHash).toBe(orchestratorManifest.modelHash);
      }
    });
  });
});
