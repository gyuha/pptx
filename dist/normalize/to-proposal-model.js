"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeToProposalModel = exports.NormalizationContractError = void 0;
const proposal_model_1 = require("../domain/proposal-model");
class NormalizationContractError extends Error {
    code;
    constructor(code, message) {
        super(message);
        this.name = 'NormalizationContractError';
        this.code = code;
    }
}
exports.NormalizationContractError = NormalizationContractError;
const DEFAULT_AGENDA = [
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
};
const HEADING_PATTERN = /^#{1,6}\s+(.+)$/;
const normalizeText = (value) => value.replace(/\s+/g, ' ').trim();
const isHeadingLine = (line) => HEADING_PATTERN.test(line);
const getHeadingText = (line) => {
    const match = line.match(HEADING_PATTERN);
    return match ? normalizeText(match[1]) : undefined;
};
const collectSectionLines = (lines, headingMatcher) => {
    const headingIndex = lines.findIndex((line) => {
        const heading = getHeadingText(line);
        return heading ? headingMatcher(heading.toLowerCase()) : false;
    });
    if (headingIndex < 0) {
        return [];
    }
    const sectionLines = [];
    for (const line of lines.slice(headingIndex + 1)) {
        if (isHeadingLine(line)) {
            break;
        }
        sectionLines.push(line);
    }
    return sectionLines;
};
const extractListItems = (lines) => lines
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
const extractSectionText = (lines) => {
    const normalized = lines
        .map((line) => normalizeText(line))
        .filter((line) => line.length > 0)
        .map((line) => line.replace(/^[-*+]\s+/, '').replace(/^\d+[.)]\s+/, ''));
    if (normalized.length === 0) {
        return undefined;
    }
    return normalizeText(normalized.join(' '));
};
const extractLabeledValue = (lines, label) => {
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
const extractTitle = (lines) => {
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
const extractSectionWithAliases = (lines, aliases) => {
    for (const alias of aliases) {
        const sectionLines = collectSectionLines(lines, (heading) => heading.includes(alias));
        if (sectionLines.length > 0) {
            return sectionLines;
        }
    }
    return [];
};
const normalizeMergedMarkdown = (parsedDocuments) => {
    const orderedDocuments = [...parsedDocuments].sort((a, b) => a.sourceFile.localeCompare(b.sourceFile));
    const merged = orderedDocuments
        .map((document) => document.markdown.trim())
        .filter((markdown) => markdown.length > 0)
        .join('\n\n');
    if (merged.length === 0) {
        throw new NormalizationContractError('NORMALIZATION_EMPTY_INPUT', 'NORMALIZATION_EMPTY_INPUT: expected at least one parsed document with non-empty markdown');
    }
    return merged;
};
const normalizeToProposalModel = ({ parsedDocuments, }) => {
    const mergedMarkdown = normalizeMergedMarkdown(parsedDocuments);
    const lines = mergedMarkdown.split(/\r?\n/);
    const agendaLines = extractSectionWithAliases(lines, ['agenda']);
    const valuePropositionLines = extractSectionWithAliases(lines, ['value proposition', 'value']);
    const executionPlanLines = extractSectionWithAliases(lines, ['execution plan', 'implementation plan', 'delivery plan']);
    const budgetTimelineLines = extractSectionWithAliases(lines, ['budget & timeline', 'budget and timeline', 'budget', 'timeline']);
    const agenda = extractListItems(agendaLines);
    const valueProposition = extractSectionText(valuePropositionLines);
    const executionPlan = extractSectionText(executionPlanLines);
    const budget = extractLabeledValue(budgetTimelineLines, 'budget') ??
        extractLabeledValue(lines, 'budget') ??
        DEFAULT_PLACEHOLDERS.budget;
    const timeline = extractLabeledValue(budgetTimelineLines, 'timeline') ??
        extractLabeledValue(lines, 'timeline') ??
        DEFAULT_PLACEHOLDERS.timeline;
    return (0, proposal_model_1.validateProposalModel)({
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
exports.normalizeToProposalModel = normalizeToProposalModel;
