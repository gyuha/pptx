#!/usr/bin/env node
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

interface EvidenceEntry {
  task: string;
  timestamp: string;
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

const collectEvidence = (args: string[]): void => {
  const taskName = args[0] ?? 'unknown';
  const command = args[1] ?? 'echo "no command specified"';
  const evidenceDir = resolve(process.cwd(), '.sisyphus', 'evidence');
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidencePath = resolve(evidenceDir, `${taskName}-${timestamp}.log`);

  mkdirSync(evidenceDir, { recursive: true });

  const { spawn } = require('node:child_process');
  const result = spawn('sh', ['-c', command], {
    cwd: process.cwd(),
    env: { ...process.env },
  });

  let stdout = '';
  let stderr = '';

  result.stdout?.on('data', (data: Buffer) => {
    stdout += data.toString();
  });

  result.stderr?.on('data', (data: Buffer) => {
    stderr += data.toString();
  });

  result.on('close', (code: number | null) => {
    const entry: EvidenceEntry = {
      task: taskName,
      timestamp: new Date().toISOString(),
      exitCode: code,
      stdout,
      stderr,
    };

    writeFileSync(evidencePath, JSON.stringify(entry, null, 2));
    process.exit(code ?? 1);
  });
};

collectEvidence(process.argv.slice(2));
