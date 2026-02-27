"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.makeProposalCommand = void 0;
const run_proposal_pipeline_1 = require("../orchestrator/run-proposal-pipeline");
/**
 * Dedicated slash command route for "제작해줘" (make proposal).
 * This is the single orchestration entrypoint used by both the slash command
 * and the CLI, ensuring identical behavior.
 *
 * @param options - Command options including input, output, and template paths
 * @returns Result object with success status and either error or result data
 */
const makeProposalCommand = async (options) => {
    try {
        const result = await (0, run_proposal_pipeline_1.runProposalPipeline)({
            cliInputPath: options.input,
            cliOutputPath: options.output,
            cliTemplatePath: options.template,
            envTemplatePath: process.env.PROPOSAL_TEMPLATE_PATH,
        });
        return {
            success: true,
            result: {
                manifestPath: result.manifestPath,
                model: result.model,
                pptxPath: result.pptxPath,
                slideCount: result.slideCount,
            },
        };
    }
    catch (error) {
        if (error instanceof Error && 'code' in error) {
            const err = error;
            return {
                success: false,
                error: {
                    code: err.code,
                    message: err.message,
                },
            };
        }
        return {
            success: false,
            error: {
                code: 'UNKNOWN',
                message: error instanceof Error ? error.message : 'Unknown error occurred',
            },
        };
    }
};
exports.makeProposalCommand = makeProposalCommand;
