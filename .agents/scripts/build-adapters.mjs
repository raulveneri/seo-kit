#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, readdirSync, unlinkSync } from "node:fs";
import path from "node:path";
import { ROOT, MARKER, agents, fail, sha256, writeAtomic } from "./lib.mjs";

function generatedInstructions(agent) {
  const skills = agent.skills.length
    ? `\n\nRequired skills: ${agent.skills.map((skill) => `\`${skill}\``).join(", ")}. Load every matching SKILL.md in full before applying it.`
    : "";
  return `Generated from the canonical agent \`${agent.name}\`. Follow these instructions exactly.${skills}\n\n${agent.body}\n`;
}

function claude(agent) {
  // Hosts parse YAML frontmatter only at the start of the file.
  return `---\n${agent.frontmatter}\n---\n\n<!-- ${MARKER}, source-sha256: ${sha256(agent.source)} -->\n\n${agent.body}\n`;
}

function codex(agent) {
  const lines = [
    `# ${MARKER}`,
    `# source-sha256: ${sha256(agent.source)}`,
    `name = ${JSON.stringify(agent.name)}`,
    `description = ${JSON.stringify(agent.description)}`,
    `developer_instructions = ${JSON.stringify(generatedInstructions(agent))}`,
  ];
  if (/read-only|analysis\/report only/i.test(agent.description)) lines.push('sandbox_mode = "read-only"');
  return `${lines.join("\n")}\n`;
}

function opencode(agent) {
  const skills = agent.skills.length
    ? `\n\nRequired skills: ${agent.skills.map((skill) => `\`${skill}\``).join(", ")}. Load their SKILL.md files before applying them.`
    : "";
  return `---\ndescription: ${JSON.stringify(agent.description)}\nmode: subagent\n---\n\n<!-- ${MARKER}, source-sha256: ${sha256(agent.source)} -->\n\n${agent.body}${skills}\n`;
}

function syncDirectory(directory, expected) {
  mkdirSync(directory, { recursive: true });
  let changed = 0;
  for (const [filename, content] of expected) if (writeAtomic(path.join(directory, filename), content)) changed += 1;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (!entry.isFile() || expected.has(entry.name)) continue;
    const filePath = path.join(directory, entry.name);
    if (!readFileSync(filePath, "utf8").includes(MARKER)) fail(`Refusing to remove non-generated adapter: ${filePath}`);
    unlinkSync(filePath);
    changed += 1;
  }
  return changed;
}

const definitions = agents();
const outputs = [
  [path.join(ROOT, ".agents", "adapters", "claude", "agents"), new Map(definitions.map((agent) => [`${agent.name}.md`, claude(agent)]))],
  [path.join(ROOT, ".agents", "adapters", "codex", "agents"), new Map(definitions.map((agent) => [`${agent.name}.toml`, codex(agent)]))],
  [path.join(ROOT, ".agents", "adapters", "opencode", "agent"), new Map(definitions.map((agent) => [`${agent.name}.md`, opencode(agent)]))],
];

let changes = 0;
for (const [directory, expected] of outputs) changes += syncDirectory(directory, expected);
process.stdout.write(`build: ${definitions.length} agents, ${changes} adapter changes\n`);

