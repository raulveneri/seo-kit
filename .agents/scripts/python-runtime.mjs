#!/usr/bin/env node
// Keep optional audit dependencies in user-owned state, outside the repository.
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
const runtime = join(homedir(), '.local', 'share', 'seo-kit', 'runtime', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const executable = process.env.SEO_KIT_PYTHON || (existsSync(runtime) ? runtime : 'python3');
const child = spawn(executable, process.argv.slice(2), { stdio: 'inherit' });
child.on('error', error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
child.on('exit', (code, signal) => { if (signal) process.kill(process.pid, signal); else process.exitCode = code ?? 1; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
