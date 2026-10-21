#!/usr/bin/env node
// A bounded worktree check, not a history audit or a general PII classifier.
import { readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { ROOT, run } from "./lib.mjs";

const secretPatterns = [
  /\bgh[pousr]_[A-Za-z0-9]{30,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{40,}\b/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bAIza[0-9A-Za-z_-]{30,}\b/,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b/,
];

export function privateDataFindings(file, content) {
  const findings = [];
  if (/^\.agents[\\/]local(?:[\\/]|$)/.test(file)) {
    findings.push({ file, line: 1, kind: "local-only file" });
  }
  if (/(?:^|\/)\.env(?:\.|$)/.test(file) && !file.endsWith(".env.example")) {
    findings.push({ file, line: 1, kind: "environment file" });
  }
  content.split(/\r?\n/).forEach((line, index) => {
    const add = (kind) => findings.push({ file, line: index + 1, kind });
    if (secretPatterns.some((pattern) => pattern.test(line))) add("credential format");
    const emails = line.match(/[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) ?? [];
    if (emails.some((email) => !/(?:@|\.)(?:example\.(?:com|org|net|test)|test|invalid|localhost|noreply\.github\.com)$/i.test(email))) add("non-example email address");
    const homes = line.match(/\/(?:home|Users)\/[A-Za-z0-9_.-]+|[A-Za-z]:\\{1,2}Users\\{1,2}[A-Za-z0-9_.'-]+/g) ?? [];
    if (homes.some((home) => !(file.startsWith(".agents/tests/") && /(?:\/|\\)(?:alice|Alice|O'Neil)$/.test(home)))) add("personal home path");
  });
  return findings;
}

export function checkPrivateData(root = ROOT) {
  const files = run("git", ["ls-files", "--cached", "--others", "--exclude-standard", "-z"], { cwd: root }).stdout.split("\0").filter(Boolean);
  const findings = [];
  for (const file of new Set(files)) {
    let content;
    try { content = readFileSync(path.join(root, file)); }
    catch (error) { if (error.code === "ENOENT") continue; throw error; }
    findings.push(...privateDataFindings(file, content.includes(0) ? "" : content.toString("utf8")));
  }
  return findings;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const findings = checkPrivateData();
  // Never print matching lines or credential values.
  for (const finding of findings) process.stderr.write(`${finding.file}:${finding.line}: ${finding.kind}\n`);
  process.stdout.write(`private-data: ${findings.length ? "FAIL" : "PASS"} (worktree patterns, Git history not checked)\n`);
  process.exitCode = findings.length ? 1 : 0;
}
