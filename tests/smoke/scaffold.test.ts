import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('scaffold', () => {
  it('has required npm scripts', () => {
    const packageJsonPath = resolve(process.cwd(), 'package.json');
    const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf8')) as {
      scripts?: Record<string, string>;
    };

    expect(packageJson.scripts?.build).toBeTypeOf('string');
    expect(packageJson.scripts?.typecheck).toBeTypeOf('string');
    expect(packageJson.scripts?.test).toBeTypeOf('string');
    expect(packageJson.scripts?.['proposal:make']).toBeTypeOf('string');
  });
});
