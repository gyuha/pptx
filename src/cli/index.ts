#!/usr/bin/env node

import { runProposalPipeline } from '../orchestrator/run-proposal-pipeline';
import { TemplateConfigError } from '../config/runtime-config';
import { IoContractError } from '../io/errors';
import { RendererError } from '../render/pptx-renderer';
import { NormalizationContractError } from '../normalize/to-proposal-model';
import { ParserContractError } from '../parsers/errors';

interface CliArgs {
  help?: boolean;
  input?: string;
  output?: string;
  template?: string;
}

const parseArgs = (): CliArgs => {
  const args = process.argv.slice(2);
  const result: CliArgs = {};

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--help':
      case '-h':
        result.help = true;
        break;
      case '--input':
      case '-i':
        result.input = args[++i];
        break;
      case '--output':
      case '-o':
        result.output = args[++i];
        break;
      case '--template':
      case '-t':
        result.template = args[++i];
        break;
      default:
        if (arg.startsWith('-')) {
          console.error(`Unknown option: ${arg}`);
          process.exit(1);
        }
    }
  }

  return result;
};

const showHelp = (): void => {
  console.log(`
proposal:make - Generate PPTX proposal from RPF documents

USAGE:
  proposal:make [OPTIONS]

OPTIONS:
  -i, --input <dir>       (required) Input directory containing PDF/DOCX RPF files
  -o, --output <dir>      (optional) Output directory for generated files [default: output]
  -t, --template <path>   (optional) Path to PPTX template file [default: input/template.pptx]
  -h, --help              Show this help message

ENVIRONMENT VARIABLES:
  PROPOSAL_TEMPLATE_PATH  Default template path (overridden by --template)

EXAMPLES:
  # Generate proposal from input/ directory
  proposal:make --input ./input

  # Specify custom output directory
  proposal:make --input ./input --output ./dist/proposals

  # Use custom template
  proposal:make --input ./input --template ./company-template.pptx

  # All options combined
  proposal:make -i ./fixtures/input -o ./tmp/output -t ./templates/default.pptx

EXIT CODES:
  0 - Success
  1 - Error (check error message for details)
`);
};

const main = async (): Promise<number> => {
  const args = parseArgs();

  if (args.help) {
    showHelp();
    return 0;
  }

  if (!args.input) {
    console.error('Error: --input is required\n');
    showHelp();
    return 1;
  }

  try {
    const result = await runProposalPipeline({
      cliInputPath: args.input,
      cliOutputPath: args.output,
      cliTemplatePath: args.template,
      envTemplatePath: process.env.PROPOSAL_TEMPLATE_PATH,
    });

    console.log(`Generated proposal: ${result.pptxPath}`);
    console.log(`Manifest: ${result.manifestPath}`);
    console.log(`Slides: ${result.slideCount}`);

    return 0;
  } catch (error) {
    if (error instanceof IoContractError) {
      console.error(`Error: [${error.code}] ${error.message}`);
    } else if (error instanceof TemplateConfigError) {
      console.error(`Error: [${error.code}] ${error.message}`);
    } else if (error instanceof ParserContractError) {
      console.error(`Error: [${error.code}] ${error.message}`);
    } else if (error instanceof NormalizationContractError) {
      console.error(`Error: [${error.code}] ${error.message}`);
    } else if (error instanceof RendererError) {
      console.error(`Error: [${error.code}] ${error.message}`);
    } else if (error instanceof Error) {
      console.error(`Error: ${error.message}`);
    } else {
      console.error('Unknown error occurred');
    }
    return 1;
  }
};

main()
  .then((exitCode) => process.exit(exitCode))
  .catch(() => process.exit(1));
