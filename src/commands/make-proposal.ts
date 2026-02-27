import { runProposalPipeline } from '../orchestrator/run-proposal-pipeline';
import type { ProposalModel } from '../domain/proposal-model';

export interface MakeProposalCommandOptions {
  input: string;
  output?: string;
  template?: string;
}

export interface MakeProposalCommandResult {
  success: boolean;
  error?: {
    code: string;
    message: string;
  };
  result?: {
    manifestPath: string;
    model: ProposalModel;
    pptxPath: string;
    slideCount: number;
  };
}

/**
 * Dedicated slash command route for "제작해줘" (make proposal).
 * This is the single orchestration entrypoint used by both the slash command
 * and the CLI, ensuring identical behavior.
 *
 * @param options - Command options including input, output, and template paths
 * @returns Result object with success status and either error or result data
 */
export const makeProposalCommand = async (
  options: MakeProposalCommandOptions
): Promise<MakeProposalCommandResult> => {
  try {
    const result = await runProposalPipeline({
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
  } catch (error) {
    if (error instanceof Error && 'code' in error) {
      const err = error as { code: string; message: string };
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
