#!/usr/bin/env node
import validator from 'amphtml-validator';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
let data = '';
for await (const chunk of process.stdin) data += chunk;
const instance = await validator.getInstance(process.argv[2]);
const result = instance.validateString(data);
process.stdout.write(JSON.stringify({ status: result.status, validator_sha256: createHash('sha256').update(await readFile(process.argv[2])).digest('hex'), errors: result.errors.map(error => ({ severity: error.severity, line: error.line, column: error.col, message: error.message, code: error.code, spec_url: error.specUrl })) }));
