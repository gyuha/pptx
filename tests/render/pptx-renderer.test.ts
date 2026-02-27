import { describe, it, expect, beforeAll } from 'vitest';
import { promises as fs } from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';
import { renderProposalToPptx, RendererError } from '../../src/render/pptx-renderer';
import type { ProposalModel } from '../../src/domain/proposal-model';

const FIXTURES_DIR = path.join(__dirname, '../fixtures/render');
const OUTPUT_DIR = path.join(FIXTURES_DIR, 'output');

const VALID_PROPOSAL_MODEL: ProposalModel = {
  title: 'Test Proposal Title',
  agenda: ['First agenda item', 'Second agenda item', 'Third agenda item'],
  valueProposition: 'This is a comprehensive value proposition that demonstrates the unique benefits of our solution.',
  executionPlan: 'Phase 1: Initial setup. Phase 2: Implementation. Phase 3: Deployment and monitoring.',
  budgetTimeline: {
    budget: '50,000 USD',
    timeline: '3 months',
  },
};

describe('pptx-renderer', () => {
  beforeAll(async () => {
    await fs.mkdir(OUTPUT_DIR, { recursive: true });
  });

  describe('happy path', () => {
    it('should create a valid pptx file with correct structure', async () => {
      const outputPath = path.join(OUTPUT_DIR, 'test-proposal.pptx');
      const manifest = await renderProposalToPptx({
        model: VALID_PROPOSAL_MODEL,
        outputPath,
        templateHash: 'test-template',
      });

      expect(manifest.modelHash).toMatch(/^[a-f0-9]{64}$/);
      expect(manifest.templateHash).toBe('test-template');
      expect(manifest.outputFile).toBe(outputPath);
      expect(manifest.slideCount).toBeGreaterThan(0);
      expect(manifest.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);

      const fileExists = await fs
        .access(outputPath)
        .then(() => true)
        .catch(() => false);
      expect(fileExists).toBe(true);

      const zip = new AdmZip(outputPath);
      const entries = zip.getEntries();

      const hasPresentationXml = entries.some((e) => e.entryName.includes('ppt/presentation.xml'));
      const hasContentTypes = entries.some((e) => e.entryName.includes('[Content_Types].xml'));

      expect(hasPresentationXml).toBe(true);
      expect(hasContentTypes).toBe(true);
    });

    it('should include all manifest fields', async () => {
      const outputPath = path.join(OUTPUT_DIR, 'manifest-test.pptx');
      const manifest = await renderProposalToPptx({
        model: VALID_PROPOSAL_MODEL,
        outputPath,
        templateHash: 'abc123',
      });

      expect(manifest).toMatchObject({
        modelHash: expect.any(String),
        templateHash: 'abc123',
        outputFile: outputPath,
        slideCount: expect.any(Number),
        timestamp: expect.any(String),
      });
    });

    it('should apply custom branding config', async () => {
      const outputPath = path.join(OUTPUT_DIR, 'branded-test.pptx');
      const manifest = await renderProposalToPptx({
        model: VALID_PROPOSAL_MODEL,
        outputPath,
        branding: {
          primaryColor: 'FF0000',
          fontFamily: 'Helvetica',
          titleFontSize: 40,
        },
      });

      expect(manifest.slideCount).toBeGreaterThan(0);
    });
  });

  describe('failure scenarios', () => {
    it('should throw MODEL_VALIDATION_FAILED for invalid model', async () => {
      const outputPath = path.join(OUTPUT_DIR, 'invalid-test.pptx');

      await expect(
        renderProposalToPptx({
          model: { invalid: 'data' },
          outputPath,
        })
      ).rejects.toThrow(RendererError);

      await expect(
        renderProposalToPptx({
          model: { invalid: 'data' },
          outputPath,
        })
      ).rejects.toMatchObject({
        code: 'MODEL_VALIDATION_FAILED',
        name: 'RendererError',
      });
    });

    it('should throw MODEL_VALIDATION_FAILED for missing required field', async () => {
      const outputPath = path.join(OUTPUT_DIR, 'missing-field-test.pptx');
      const invalidModel = {
        ...VALID_PROPOSAL_MODEL,
        title: '', // Empty title should fail validation
      };

      await expect(
        renderProposalToPptx({
          model: invalidModel,
          outputPath,
        })
      ).rejects.toThrow(RendererError);

      await expect(
        renderProposalToPptx({
          model: invalidModel,
          outputPath,
        })
      ).rejects.toMatchObject({
        code: 'MODEL_VALIDATION_FAILED',
      });
    });

    it('should throw MODEL_VALIDATION_FAILED for missing budgetTimeline', async () => {
      const outputPath = path.join(OUTPUT_DIR, 'no-budget-test.pptx');

      const invalidModel = {
        title: 'Test',
        agenda: ['item'],
        valueProposition: 'value',
        executionPlan: 'plan',
      };

      await expect(
        renderProposalToPptx({
          model: invalidModel,
          outputPath,
        })
      ).rejects.toThrow(RendererError);
    });
  });

  describe('determinism', () => {
    it('should produce identical modelHash for identical models', async () => {
      const outputPath1 = path.join(OUTPUT_DIR, 'deterministic-1.pptx');
      const outputPath2 = path.join(OUTPUT_DIR, 'deterministic-2.pptx');

      const manifest1 = await renderProposalToPptx({
        model: VALID_PROPOSAL_MODEL,
        outputPath: outputPath1,
      });

      const manifest2 = await renderProposalToPptx({
        model: VALID_PROPOSAL_MODEL,
        outputPath: outputPath2,
      });

      expect(manifest1.modelHash).toBe(manifest2.modelHash);
      expect(manifest1.slideCount).toBe(manifest2.slideCount);
    });
  });
});
