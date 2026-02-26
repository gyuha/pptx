#!/usr/bin/env node

const { accessSync, constants, existsSync } = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const MIN_NODE_MAJOR = 20;
const MIN_NPM_MAJOR = 10;

const projectRoot = path.resolve(__dirname, '..');
const env = process.env;

const failures = [];
const warnings = [];

const toBool = (value) => /^(1|true|yes|on)$/i.test(String(value ?? '').trim());

const addFailure = (message, remediation) => {
  failures.push({ message, remediation });
};

const addWarning = (message) => {
  warnings.push(message);
};

const logOk = (label, details) => {
  const suffix = details ? `: ${details}` : '';
  console.log(`[OK] ${label}${suffix}`);
};

const run = (command, args) =>
  spawnSync(command, args, {
    cwd: projectRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });

const checkNode = () => {
  const current = process.versions.node;
  const major = Number(current.split('.')[0]);

  if (!Number.isFinite(major) || major < MIN_NODE_MAJOR) {
    addFailure(
      `Node.js ${current} is not supported`,
      `Install Node.js ${MIN_NODE_MAJOR}.x or newer, then rerun npm run proposal:doctor.`
    );
    return;
  }

  logOk('Node.js runtime', current);
};

const checkNpm = () => {
  const result = run('npm', ['--version']);
  const version = `${result.stdout}`.trim();

  if (result.status !== 0 || !version) {
    addFailure('npm is not available', 'Install npm and ensure it is on PATH.');
    return;
  }

  const major = Number(version.split('.')[0]);
  if (!Number.isFinite(major) || major < MIN_NPM_MAJOR) {
    addFailure(
      `npm ${version} is not supported`,
      `Install npm ${MIN_NPM_MAJOR}.x or newer, then rerun npm run proposal:doctor.`
    );
    return;
  }

  logOk('npm runtime', version);
};

const checkMarkItDownRuntime = () => {
  const pythonCheck = run('python3', ['--version']);
  if (pythonCheck.status !== 0) {
    addFailure(
      'python3 is required for MarkItDown runtime checks',
      'Install Python 3.10+ and ensure python3 is on PATH.'
    );
    return;
  }

  const importCheck = run('python3', [
    '-c',
    'import markitdown,sys;sys.stdout.write(getattr(markitdown,"__version__","unknown"))',
  ]);

  if (importCheck.status !== 0) {
    addFailure(
      'MarkItDown package is not importable',
      "Install with: python3 -m pip install 'markitdown[pdf,docx,pptx]==0.1.5'"
    );
    return;
  }

  const version = `${importCheck.stdout}`.trim() || 'unknown';
  logOk('MarkItDown runtime', version);
};

const checkTemplateAccessibility = () => {
  const templateFromEnv = env.PROPOSAL_TEMPLATE_PATH;
  const templatePath = templateFromEnv
    ? path.resolve(projectRoot, templateFromEnv)
    : path.join(projectRoot, 'input', 'template.pptx');

  if (!existsSync(templatePath)) {
    const sourceLabel = templateFromEnv ? 'PROPOSAL_TEMPLATE_PATH' : 'input/template.pptx';
    addFailure(
      `Template file not found (${sourceLabel})`,
      `Create a readable template file or set PROPOSAL_TEMPLATE_PATH to an existing file. Checked path: ${templatePath}`
    );
    return;
  }

  try {
    accessSync(templatePath, constants.R_OK);
  } catch {
    addFailure(
      'Template file exists but is not readable',
      `Fix file permissions for: ${templatePath}`
    );
    return;
  }

  logOk('Template accessibility', path.relative(projectRoot, templatePath));
};

const checkOptionalMcpPolicy = () => {
  const enabled = toBool(env.PROPOSAL_ENABLE_MARKITDOWN_MCP);
  if (!enabled) {
    logOk('Optional MarkItDown MCP policy', 'disabled by default');
    return;
  }

  const host = `${env.PROPOSAL_MARKITDOWN_MCP_HOST ?? '127.0.0.1'}`.trim();
  const allowedHosts = new Set(['127.0.0.1', 'localhost', '::1']);
  if (!allowedHosts.has(host)) {
    addFailure(
      `Invalid MCP host: ${host}`,
      'Set PROPOSAL_MARKITDOWN_MCP_HOST to 127.0.0.1, localhost, or ::1. Never expose without authenticated gateway.'
    );
  }

  const command = `${env.PROPOSAL_MARKITDOWN_MCP_COMMAND ?? ''}`.trim();
  if (!command) {
    addFailure(
      'PROPOSAL_ENABLE_MARKITDOWN_MCP is set, but PROPOSAL_MARKITDOWN_MCP_COMMAND is missing',
      'Set PROPOSAL_MARKITDOWN_MCP_COMMAND to an executable on PATH, for example: python3'
    );
    return;
  }

  const check = run('bash', ['-lc', `command -v ${JSON.stringify(command)}`]);
  if (check.status !== 0) {
    addFailure(
      `Configured MCP command is not executable: ${command}`,
      'Install the command, or set PROPOSAL_MARKITDOWN_MCP_COMMAND to a valid executable path.'
    );
    return;
  }

  const args = `${env.PROPOSAL_MARKITDOWN_MCP_ARGS ?? ''}`.trim();
  logOk(
    'Optional MarkItDown MCP command',
    args ? `${command} ${args}` : command
  );
};

const runDoctor = () => {
  checkNode();
  checkNpm();
  checkMarkItDownRuntime();
  checkTemplateAccessibility();
  checkOptionalMcpPolicy();

  warnings.forEach((warning) => {
    console.warn(`[WARN] ${warning}`);
  });

  if (failures.length > 0) {
    failures.forEach((failure, index) => {
      console.error(`[FAIL ${index + 1}] ${failure.message}`);
      console.error(`  Remediation: ${failure.remediation}`);
    });
    console.error(`\nproposal:doctor failed with ${failures.length} issue(s).`);
    process.exit(1);
  }

  console.log('\nproposal:doctor passed. Required tooling and policy checks are satisfied.');
};

runDoctor();
