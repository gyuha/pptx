export interface BudgetTimelinePlaceholder {
  budget: string;
  timeline: string;
}

export interface ProposalModel {
  title: string;
  agenda: string[];
  valueProposition: string;
  executionPlan: string;
  budgetTimeline: BudgetTimelinePlaceholder;
}

export type ProposalModelValidationErrorCode =
  | 'PROPOSAL_MODEL_INVALID_TYPE'
  | 'PROPOSAL_MODEL_REQUIRED_FIELD_MISSING'
  | 'PROPOSAL_MODEL_INVALID_FIELD_TYPE';

export class ProposalModelValidationError extends Error {
  readonly code: ProposalModelValidationErrorCode;
  readonly field: string;

  constructor(code: ProposalModelValidationErrorCode, message: string, field: string) {
    super(message);
    this.name = 'ProposalModelValidationError';
    this.code = code;
    this.field = field;
  }
}

const REQUIRED_FIELDS: ReadonlyArray<keyof ProposalModel> = [
  'title',
  'agenda',
  'valueProposition',
  'executionPlan',
  'budgetTimeline',
];

const isObjectRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isNonEmptyString = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0;

const validateBudgetTimeline = (value: unknown): BudgetTimelinePlaceholder => {
  if (!isObjectRecord(value)) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE',
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE: field "budgetTimeline" must be an object with non-empty string properties "budget" and "timeline"',
      'budgetTimeline'
    );
  }

  if (!isNonEmptyString(value.budget) || !isNonEmptyString(value.timeline)) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE',
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE: field "budgetTimeline" must be an object with non-empty string properties "budget" and "timeline"',
      'budgetTimeline'
    );
  }

  return {
    budget: value.budget,
    timeline: value.timeline,
  };
};

export const validateProposalModel = (input: unknown): ProposalModel => {
  if (!isObjectRecord(input)) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_TYPE',
      'PROPOSAL_MODEL_INVALID_TYPE: expected a plain object for ProposalModel',
      'root'
    );
  }

  for (const field of REQUIRED_FIELDS) {
    if (!(field in input)) {
      throw new ProposalModelValidationError(
        'PROPOSAL_MODEL_REQUIRED_FIELD_MISSING',
        `PROPOSAL_MODEL_REQUIRED_FIELD_MISSING: missing required field "${field}"`,
        field
      );
    }
  }

  if (!isNonEmptyString(input.title)) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE',
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE: field "title" must be a non-empty string',
      'title'
    );
  }

  if (!Array.isArray(input.agenda) || input.agenda.length === 0 || input.agenda.some((item) => !isNonEmptyString(item))) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE',
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE: field "agenda" must be a non-empty array of non-empty strings',
      'agenda'
    );
  }

  if (!isNonEmptyString(input.valueProposition)) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE',
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE: field "valueProposition" must be a non-empty string',
      'valueProposition'
    );
  }

  if (!isNonEmptyString(input.executionPlan)) {
    throw new ProposalModelValidationError(
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE',
      'PROPOSAL_MODEL_INVALID_FIELD_TYPE: field "executionPlan" must be a non-empty string',
      'executionPlan'
    );
  }

  return {
    title: input.title,
    agenda: input.agenda,
    valueProposition: input.valueProposition,
    executionPlan: input.executionPlan,
    budgetTimeline: validateBudgetTimeline(input.budgetTimeline),
  };
};
