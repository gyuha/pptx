import type { ProposalModel } from '../domain/proposal-model';
import { validateProposalModel } from '../domain/proposal-model';
import type { ParsedInputDocument } from '../parsers/markitdown-adapter';

export type NormalizationErrorCode = 'NORMALIZATION_EMPTY_INPUT';

export class NormalizationContractError extends Error {
  readonly code: NormalizationErrorCode;

  constructor(code: NormalizationErrorCode, message: string) {
    super(message);
    this.name = 'NormalizationContractError';
    this.code = code;
  }
}

export interface NormalizeToProposalModelParams {
  parsedDocuments: ReadonlyArray<ParsedInputDocument>;
}

const DEFAULT_AGENDA: ReadonlyArray<string> = [
  'Context and business goals',
  'Recommended solution',
  'Execution roadmap',
  'Budget and timeline',
];

const DEFAULT_PLACEHOLDERS = {
  budget: 'Budget to be confirmed',
  executionPlan: 'Execution plan details to be confirmed',
  timeline: 'Timeline to be confirmed',
  title: 'Untitled proposal',
  valueProposition: 'Value proposition details to be confirmed',
} as const;

const HEADING_PATTERN = /^#{1,6}\s+(.+)$/;

const normalizeText = (value: string): string => value.replace(/\s+/g, ' ').trim();

const isHeadingLine = (line: string): boolean => HEADING_PATTERN.test(line);

const getHeadingText = (line: string): string | undefined => {
  const match = line.match(HEADING_PATTERN);
  return match ? normalizeText(match[1]) : undefined;
};

const collectSectionLines = (
  lines: ReadonlyArray<string>,
  headingMatcher: (heading: string) => boolean
): string[] => {
  const headingIndex = lines.findIndex((line) => {
    const heading = getHeadingText(line);
    return heading ? headingMatcher(heading.toLowerCase()) : false;
  });

  if (headingIndex < 0) {
    return [];
  }

  const sectionLines: string[] = [];
  for (const line of lines.slice(headingIndex + 1)) {
    if (isHeadingLine(line)) {
      break;
    }

    sectionLines.push(line);
  }

  return sectionLines;
};

const extractListItems = (lines: ReadonlyArray<string>): string[] =>
  lines
    .map((line) => normalizeText(line))
    .filter((line) => line.length > 0)
    .map((line) => {
      const bulletMatch = line.match(/^[-*+]\s+(.+)$/);
      if (bulletMatch) {
        return normalizeText(bulletMatch[1]);
      }

      const numberedMatch = line.match(/^\d+[.)]\s+(.+)$/);
      if (numberedMatch) {
        return normalizeText(numberedMatch[1]);
      }

      return '';
    })
    .filter((line) => line.length > 0);

const extractSectionText = (lines: ReadonlyArray<string>): string | undefined => {
  const normalized = lines
    .map((line) => normalizeText(line))
    .filter((line) => line.length > 0)
    .map((line) => line.replace(/^[-*+]\s+/, '').replace(/^\d+[.)]\s+/, ''));

  if (normalized.length === 0) {
    return undefined;
  }

  return normalizeText(normalized.join(' '));
};

const extractLabeledValue = (lines: ReadonlyArray<string>, label: 'budget' | 'timeline'): string | undefined => {
  const pattern = new RegExp(`^${label}\\s*[:\\-]\\s*(.+)$`, 'i');

  for (const line of lines) {
    const normalizedLine = normalizeText(line);
    const match = normalizedLine.match(pattern);

    if (match) {
      const extracted = normalizeText(match[1]);
      if (extracted.length > 0) {
        return extracted;
      }
    }
  }

  return undefined;
};

const extractTitle = (lines: ReadonlyArray<string>): string | undefined => {
  // First, look for H1 headings (# Title) - highest priority
  const h1Pattern = /^#\s+(.+)$/;
  const h1Title = lines
    .map((line) => {
      const match = line.match(h1Pattern);
      return match ? normalizeText(match[1]) : undefined;
    })
    .find((heading) => Boolean(heading && heading.length > 0));

  if (h1Title) {
    return h1Title;
  }

  // Fall back to any heading (H2-H6) if no H1 found
  const anyHeadingTitle = lines
    .map((line) => getHeadingText(line))
    .find((heading) => Boolean(heading && heading.length > 0));

  if (anyHeadingTitle) {
    return anyHeadingTitle;
  }

  // Finally, fall back to first non-empty text line
  const firstTextLine = lines.map((line) => normalizeText(line)).find((line) => line.length > 0);
  return firstTextLine;
};

const extractSectionWithAliases = (
  lines: ReadonlyArray<string>,
  aliases: ReadonlyArray<string>
): string[] => {
  for (const alias of aliases) {
    const sectionLines = collectSectionLines(lines, (heading) => heading.includes(alias));
    if (sectionLines.length > 0) {
      return sectionLines;
    }
  }

  return [];
};

const normalizeMergedMarkdown = (parsedDocuments: ReadonlyArray<ParsedInputDocument>): string => {
  const orderedDocuments = [...parsedDocuments].sort((a, b) => a.sourceFile.localeCompare(b.sourceFile));

  const merged = orderedDocuments
    .map((document) => document.markdown.trim())
    .filter((markdown) => markdown.length > 0)
    .join('\n\n');

  if (merged.length === 0) {
    throw new NormalizationContractError(
      'NORMALIZATION_EMPTY_INPUT',
      'NORMALIZATION_EMPTY_INPUT: expected at least one parsed document with non-empty markdown'
    );
  }

  return merged;
};

export const normalizeToProposalModel = ({
  parsedDocuments,
}: NormalizeToProposalModelParams): ProposalModel => {
  const mergedMarkdown = normalizeMergedMarkdown(parsedDocuments);
  const lines = mergedMarkdown.split(/\r?\n/);

  const agendaLines = extractSectionWithAliases(lines, ['agenda']);
  const valuePropositionLines = extractSectionWithAliases(lines, ['value proposition', 'value']);
  const executionPlanLines = extractSectionWithAliases(lines, ['execution plan', 'implementation plan', 'delivery plan']);
  const budgetTimelineLines = extractSectionWithAliases(lines, ['budget & timeline', 'budget and timeline', 'budget', 'timeline']);

  const agenda = extractListItems(agendaLines);
  const valueProposition = extractSectionText(valuePropositionLines);
  const executionPlan = extractSectionText(executionPlanLines);
  const budget =
    extractLabeledValue(budgetTimelineLines, 'budget') ??
    extractLabeledValue(lines, 'budget') ??
    DEFAULT_PLACEHOLDERS.budget;
  const timeline =
    extractLabeledValue(budgetTimelineLines, 'timeline') ??
    extractLabeledValue(lines, 'timeline') ??
    DEFAULT_PLACEHOLDERS.timeline;

  return validateProposalModel({
    title: extractTitle(lines) ?? DEFAULT_PLACEHOLDERS.title,
    agenda: agenda.length > 0 ? agenda : [...DEFAULT_AGENDA],
    budgetTimeline: {
      budget,
      timeline,
    },
    executionPlan: executionPlan ?? DEFAULT_PLACEHOLDERS.executionPlan,
    valueProposition: valueProposition ?? DEFAULT_PLACEHOLDERS.valueProposition,
  });
};
