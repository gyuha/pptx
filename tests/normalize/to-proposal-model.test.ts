import { describe, expect, it } from 'vitest';

import type { ParsedInputDocument } from '../../src/parsers';
import { NormalizationContractError, normalizeToProposalModel } from '../../src/normalize';

describe('normalize/to-proposal-model', () => {
  it('produces deterministic output across reruns and input ordering', () => {
    const parsedDocuments: ParsedInputDocument[] = [
      {
        markdown: [
          '# ACME Cloud Modernization Proposal',
          '',
          '## Value Proposition',
          'Reduce costs and improve release reliability across teams.',
          '',
          '## Agenda',
          '- Business context',
          '- Proposed architecture',
        ].join('\n'),
        sourceFile: 'b-second.pdf',
      },
      {
        markdown: [
          '## Execution Plan',
          'Deliver in discovery, pilot, and rollout phases.',
          '',
          '## Budget & Timeline',
          'Budget: USD 120,000',
          'Timeline: 16 weeks',
        ].join('\n'),
        sourceFile: 'a-first.docx',
      },
    ];

    const firstRun = normalizeToProposalModel({ parsedDocuments });
    const secondRun = normalizeToProposalModel({ parsedDocuments: [...parsedDocuments].reverse() });

    expect(firstRun).toEqual(secondRun);
    expect(firstRun).toEqual({
      title: 'ACME Cloud Modernization Proposal',
      agenda: ['Business context', 'Proposed architecture'],
      valueProposition: 'Reduce costs and improve release reliability across teams.',
      executionPlan: 'Deliver in discovery, pilot, and rollout phases.',
      budgetTimeline: {
        budget: 'USD 120,000',
        timeline: '16 weeks',
      },
    });
  });

  it('fills explicit placeholders when required sections are missing', () => {
    const parsedDocuments: ParsedInputDocument[] = [
      {
        markdown: '# Draft response for Project Atlas\n\nInitial notes only.',
        sourceFile: 'single.pdf',
      },
    ];

    const model = normalizeToProposalModel({ parsedDocuments });

    expect(model).toEqual({
      title: 'Draft response for Project Atlas',
      agenda: [
        'Context and business goals',
        'Recommended solution',
        'Execution roadmap',
        'Budget and timeline',
      ],
      valueProposition: 'Value proposition details to be confirmed',
      executionPlan: 'Execution plan details to be confirmed',
      budgetTimeline: {
        budget: 'Budget to be confirmed',
        timeline: 'Timeline to be confirmed',
      },
    });
  });

  it('fails with NORMALIZATION_EMPTY_INPUT for whitespace-only parse payload', () => {
    const run = () =>
      normalizeToProposalModel({
        parsedDocuments: [
          {
            markdown: '   \n\n\t  ',
            sourceFile: 'empty.pdf',
          },
        ],
      });

    expect(run).toThrow(NormalizationContractError);
    expect(run).toThrowError(
      'NORMALIZATION_EMPTY_INPUT: expected at least one parsed document with non-empty markdown'
    );

    try {
      run();
      throw new Error('Expected normalization to fail on empty input');
    } catch (error) {
      expect(error).toBeInstanceOf(NormalizationContractError);
      const typedError = error as NormalizationContractError;
      expect(typedError.code).toBe('NORMALIZATION_EMPTY_INPUT');
      expect(typedError.message).toBe(
        'NORMALIZATION_EMPTY_INPUT: expected at least one parsed document with non-empty markdown'
      );
    }
  });
});
