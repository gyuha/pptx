#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const run_proposal_pipeline_1 = require("../orchestrator/run-proposal-pipeline");
const runtime_config_1 = require("../config/runtime-config");
const errors_1 = require("../io/errors");
const pptx_renderer_1 = require("../render/pptx-renderer");
const to_proposal_model_1 = require("../normalize/to-proposal-model");
const errors_2 = require("../parsers/errors");
const parseArgs = () => {
    const args = process.argv.slice(2);
    const result = {};
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
const showHelp = () => {
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
const main = async () => {
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
        const result = await (0, run_proposal_pipeline_1.runProposalPipeline)({
            cliInputPath: args.input,
            cliOutputPath: args.output,
            cliTemplatePath: args.template,
            envTemplatePath: process.env.PROPOSAL_TEMPLATE_PATH,
        });
        console.log(`Generated proposal: ${result.pptxPath}`);
        console.log(`Manifest: ${result.manifestPath}`);
        console.log(`Slides: ${result.slideCount}`);
        return 0;
    }
    catch (error) {
        if (error instanceof errors_1.IoContractError) {
            console.error(`Error: [${error.code}] ${error.message}`);
        }
        else if (error instanceof runtime_config_1.TemplateConfigError) {
            console.error(`Error: [${error.code}] ${error.message}`);
        }
        else if (error instanceof errors_2.ParserContractError) {
            console.error(`Error: [${error.code}] ${error.message}`);
        }
        else if (error instanceof to_proposal_model_1.NormalizationContractError) {
            console.error(`Error: [${error.code}] ${error.message}`);
        }
        else if (error instanceof pptx_renderer_1.RendererError) {
            console.error(`Error: [${error.code}] ${error.message}`);
        }
        else if (error instanceof Error) {
            console.error(`Error: ${error.message}`);
        }
        else {
            console.error('Unknown error occurred');
        }
        return 1;
    }
};
main()
    .then((exitCode) => process.exit(exitCode))
    .catch(() => process.exit(1));
