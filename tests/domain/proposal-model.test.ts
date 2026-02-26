import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  ProposalModelValidationError,
  validateProposalModel,
} from '../../src/domain/proposal-model';

const readFixture = (name: string): unknown => {
  const fixturePath = resolve(process.cwd(), 'fixtures', 'model', name);
  return JSON.parse(readFileSync(fixturePath, 'utf8')) as unknown;
};

describe('proposal-model', () => {
  it('validates a valid proposal model fixture', () => {
    const payload = readFixture('proposal-model.valid.json');

    const validated = validateProposalModel(payload);

    expect(validated.title).toBe('RPF Response for ACME Cloud Modernization');
    expect(validated.agenda.length).toBeGreaterThan(0);
    expect(validated.budgetTimeline).toEqual({ budget: 'TBD', timeline: 'TBD' });
  });

  it('fails with deterministic code and message when valueProposition is missing', () => {
    const payload = readFixture('proposal-model.invalid-missing-value-proposition.json');

    const run = () => validateProposalModel(payload);

    expect(run).toThrow(ProposalModelValidationError);
    expect(run).toThrowError(
      'PROPOSAL_MODEL_REQUIRED_FIELD_MISSING: missing required field "valueProposition"'
    );

    try {
      run();
      throw new Error('Expected validation error');
    } catch (error) {
      expect(error).toBeInstanceOf(ProposalModelValidationError);
      const typedError = error as ProposalModelValidationError;
      expect(typedError.code).toBe('PROPOSAL_MODEL_REQUIRED_FIELD_MISSING');
      expect(typedError.field).toBe('valueProposition');
      expect(typedError.message).toBe(
        'PROPOSAL_MODEL_REQUIRED_FIELD_MISSING: missing required field "valueProposition"'
      );
    }
  });
});
