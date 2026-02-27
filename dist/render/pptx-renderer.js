"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.renderProposalToPptx = exports.RendererError = void 0;
const pptxgenjs_1 = __importDefault(require("pptxgenjs"));
const proposal_model_1 = require("../domain/proposal-model");
const crypto_1 = require("crypto");
const fs_1 = require("fs");
const path_1 = __importDefault(require("path"));
class RendererError extends Error {
    code;
    cause;
    constructor(code, message, cause) {
        super(message);
        this.name = 'RendererError';
        this.code = code;
        this.cause = cause;
    }
}
exports.RendererError = RendererError;
const DEFAULT_BRANDING = {
    primaryColor: '003366',
    secondaryColor: '6699CC',
    fontFamily: 'Arial',
    titleFontSize: 36,
    bodyFontSize: 18,
};
const computeModelHash = (model) => (0, crypto_1.createHash)('sha256').update(JSON.stringify(model)).digest('hex');
const splitTextIntoSlides = (text, maxCharsPerSlide = 500) => {
    const words = text.split(/\s+/);
    const slides = [];
    let currentSlide = '';
    for (const word of words) {
        if ((currentSlide + ' ' + word).length > maxCharsPerSlide && currentSlide.length > 0) {
            slides.push(currentSlide.trim());
            currentSlide = word;
        }
        else {
            currentSlide += (currentSlide ? ' ' : '') + word;
        }
    }
    if (currentSlide.length > 0) {
        slides.push(currentSlide.trim());
    }
    return slides.length > 0 ? slides : [text];
};
const renderProposalToPptx = async ({ model, outputPath, templateHash = 'default', branding: partialBranding = {}, }) => {
    let validatedModel;
    try {
        validatedModel = (0, proposal_model_1.validateProposalModel)(model);
    }
    catch (error) {
        if (error instanceof proposal_model_1.ProposalModelValidationError) {
            throw new RendererError('MODEL_VALIDATION_FAILED', `MODEL_VALIDATION_FAILED: ${error.message}`, error);
        }
        throw new RendererError('MODEL_VALIDATION_FAILED', 'MODEL_VALIDATION_FAILED: unknown validation error', error);
    }
    const branding = {
        ...DEFAULT_BRANDING,
        ...partialBranding,
    };
    const modelHash = computeModelHash(validatedModel);
    const timestamp = new Date().toISOString();
    const pptx = new pptxgenjs_1.default();
    pptx.author = 'Proposal Generator';
    pptx.company = 'Generated Proposal';
    pptx.subject = validatedModel.title;
    pptx.title = validatedModel.title;
    let slideCount = 0;
    // Title slide
    slideCount++;
    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: branding.primaryColor };
    titleSlide.addText(validatedModel.title, {
        x: 0.5,
        y: '40%',
        w: '90%',
        h: 1,
        fontSize: 44,
        bold: true,
        color: 'FFFFFF',
        fontFace: branding.fontFamily,
        align: 'center',
        valign: 'middle',
    });
    // Agenda slide
    slideCount++;
    const agendaSlide = pptx.addSlide();
    agendaSlide.addText('Agenda', {
        x: 0.5,
        y: 0.5,
        fontSize: branding.titleFontSize,
        bold: true,
        color: branding.primaryColor,
        fontFace: branding.fontFamily,
    });
    const agendaItems = validatedModel.agenda.map((item, index) => ({
        text: item,
        options: {
            x: 0.5,
            y: 1.5 + index * 0.5,
            fontSize: branding.bodyFontSize,
            color: '000000',
            fontFace: branding.fontFamily,
            bullet: true,
        },
    }));
    for (const item of agendaItems) {
        agendaSlide.addText(item.text, item.options);
    }
    // Value Proposition slide(s)
    const valuePropSlides = splitTextIntoSlides(validatedModel.valueProposition);
    for (let i = 0; i < valuePropSlides.length; i++) {
        slideCount++;
        const slide = pptx.addSlide();
        slide.addText('Value Proposition' + (valuePropSlides.length > 1 ? ` (${i + 1}/${valuePropSlides.length})` : ''), {
            x: 0.5,
            y: 0.5,
            fontSize: branding.titleFontSize,
            bold: true,
            color: branding.primaryColor,
            fontFace: branding.fontFamily,
        });
        slide.addText(valuePropSlides[i], {
            x: 0.5,
            y: 1.5,
            w: '90%',
            h: 4,
            fontSize: branding.bodyFontSize,
            color: '000000',
            fontFace: branding.fontFamily,
            valign: 'top',
        });
    }
    // Execution Plan slide(s)
    const executionPlanSlides = splitTextIntoSlides(validatedModel.executionPlan);
    for (let i = 0; i < executionPlanSlides.length; i++) {
        slideCount++;
        const slide = pptx.addSlide();
        slide.addText('Execution Plan' + (executionPlanSlides.length > 1 ? ` (${i + 1}/${executionPlanSlides.length})` : ''), {
            x: 0.5,
            y: 0.5,
            fontSize: branding.titleFontSize,
            bold: true,
            color: branding.primaryColor,
            fontFace: branding.fontFamily,
        });
        slide.addText(executionPlanSlides[i], {
            x: 0.5,
            y: 1.5,
            w: '90%',
            h: 4,
            fontSize: branding.bodyFontSize,
            color: '000000',
            fontFace: branding.fontFamily,
            valign: 'top',
        });
    }
    // Budget and Timeline slide
    slideCount++;
    const budgetSlide = pptx.addSlide();
    budgetSlide.addText('Budget & Timeline', {
        x: 0.5,
        y: 0.5,
        fontSize: branding.titleFontSize,
        bold: true,
        color: branding.primaryColor,
        fontFace: branding.fontFamily,
    });
    budgetSlide.addText([
        { text: 'Budget: ', options: { bold: true, fontSize: branding.bodyFontSize, color: branding.primaryColor } },
        { text: validatedModel.budgetTimeline.budget, options: { fontSize: branding.bodyFontSize, color: '000000' } },
    ], {
        x: 0.5,
        y: 1.5,
        w: '90%',
        h: 1,
        fontFace: branding.fontFamily,
    });
    budgetSlide.addText([
        { text: 'Timeline: ', options: { bold: true, fontSize: branding.bodyFontSize, color: branding.primaryColor } },
        { text: validatedModel.budgetTimeline.timeline, options: { fontSize: branding.bodyFontSize, color: '000000' } },
    ], {
        x: 0.5,
        y: 2.5,
        w: '90%',
        h: 1,
        fontFace: branding.fontFamily,
    });
    const outputDir = path_1.default.dirname(outputPath);
    try {
        await fs_1.promises.mkdir(outputDir, { recursive: true });
    }
    catch (error) {
        throw new RendererError('OUTPUT_DIRECTORY_WRITE_FAILED', `OUTPUT_DIRECTORY_WRITE_FAILED: cannot create output directory "${outputDir}"`, error);
    }
    try {
        await pptx.writeFile({ fileName: outputPath });
    }
    catch (error) {
        throw new RendererError('PPTX_GENERATION_FAILED', `PPTX_GENERATION_FAILED: failed to write PPTX file to "${outputPath}"`, error);
    }
    return {
        modelHash,
        templateHash,
        outputFile: outputPath,
        slideCount,
        timestamp,
    };
};
exports.renderProposalToPptx = renderProposalToPptx;
