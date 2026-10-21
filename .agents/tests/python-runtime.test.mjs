import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const launcher = fileURLToPath(new URL('../scripts/python-runtime.mjs', import.meta.url));

test('Python imports do not leave bytecode files in managed source directories', (t) => {
  const directory = mkdtempSync(path.join(tmpdir(), 'seo-kit-python-cache-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  writeFileSync(path.join(directory, 'cache_probe.py'), 'VALUE = 42\n');
  const env = { ...process.env };
  delete env.PYTHONDONTWRITEBYTECODE;
  delete env.PYTHONPYCACHEPREFIX;
  const result = spawnSync(process.execPath, [launcher, '-c', 'import cache_probe; print(cache_probe.VALUE)'], {
    cwd: directory, env, encoding: 'utf8', timeout: 30_000,
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  assert.equal(result.stdout.trim(), '42');
  assert.equal(existsSync(path.join(directory, '__pycache__')), false,
    'bytecode files would make the managed release fail the uninstall preflight');
});
