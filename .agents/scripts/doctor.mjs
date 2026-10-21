#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { ROOT, MARKER, agents, parseDocument, run, scalar } from "./lib.mjs";
import { installation, checkInstallation } from "./global-install.mjs";

const repositoryOnly = process.argv.includes("--repository-only");
const errors = [];
const allowedSkillKeys = new Set(["name", "description", "license", "compatibility", "metadata", "allowed-tools"]);

const skillDirectories = readdirSync(path.join(ROOT, ".agents", "skills"), { withFileTypes: true }).filter((entry) => entry.isDirectory());
const skillNames = new Set(skillDirectories.map((entry) => entry.name));

for (const entry of skillDirectories) {
  const filePath = path.join(ROOT, ".agents", "skills", entry.name, "SKILL.md");
  if (!existsSync(filePath)) {
    errors.push(`missing SKILL.md: ${filePath}`);
    continue;
  }
  try {
    const document = parseDocument(filePath);
    const name = scalar(document.frontmatter, "name");
    const description = scalar(document.frontmatter, "description");
    if (name !== entry.name) errors.push(`${filePath}: name must match directory name`);
    if (!description || description.length > 1024 || /[<>]/.test(description)) errors.push(`${filePath}: invalid description`);
    for (const line of document.frontmatter.split("\n")) {
      if (!line || /^\s/.test(line) || !line.includes(":")) continue;
      const key = line.slice(0, line.indexOf(":"));
      if (!allowedSkillKeys.has(key)) errors.push(`${filePath}: unsupported frontmatter key ${key}`);
    }
  } catch (error) {
    errors.push(error.message);
  }
}

const definitions = agents();
for (const agent of definitions) {
  if (!agent.name || !agent.description || !agent.body) errors.push(`${agent.filePath}: incomplete agent`);
  if (`${agent.name}.md` !== path.basename(agent.filePath)) errors.push(`${agent.filePath}: filename/name mismatch`);
  for (const skill of agent.skills) if (!skillNames.has(skill)) errors.push(`${agent.filePath}: missing skill ${skill}`);
}


for (const agent of definitions) {
  const expected = [
    path.join(ROOT, ".agents", "adapters", "claude", "agents", `${agent.name}.md`),
    path.join(ROOT, ".agents", "adapters", "codex", "agents", `${agent.name}.toml`),
    path.join(ROOT, ".agents", "adapters", "opencode", "agent", `${agent.name}.md`),
  ];
  for (const filePath of expected) {
    if (!existsSync(filePath) || !readFileSync(filePath, "utf8").includes(MARKER)) errors.push(`missing or invalid adapter: ${filePath}`);
  }
}

for (const directory of [path.join(ROOT, ".agents", "scripts")]) {
  for (const entry of readdirSync(directory)) {
    if (!entry.endsWith(".mjs")) continue;
    const result = run(process.execPath, ["--check", path.join(directory, entry)], { allowFailure: true });
    if (result.status !== 0) errors.push(`${entry}: ${result.stderr.trim()}`);
  }
}

// Generated TOML uses a deliberately small subset: one JSON-compatible string
// per key. Check that subset without making Python a setup prerequisite.
for (const name of readdirSync(path.join(ROOT, ".agents/adapters/codex/agents"))) {
  const file = path.join(ROOT, ".agents/adapters/codex/agents", name);
  try {
    const fields = {};
    for (const line of readFileSync(file, "utf8").split("\n")) {
      if (!line || line.startsWith("#")) continue;
      const match = line.match(/^([a-z_]+) = (".*")$/);
      if (!match) throw new Error("unsupported generated TOML syntax");
      fields[match[1]] = JSON.parse(match[2]);
    }
    for (const key of ["name", "description", "developer_instructions"]) if (!fields[key]) throw new Error(`missing ${key}`);
  } catch (error) { errors.push(`${file}: ${error.message}`); }
}

if (!repositoryOnly) {
  try {
    const ctx = installation(process.env.SEO_KIT_MANAGED_BASE ? { base: process.env.SEO_KIT_MANAGED_BASE } : {});
    errors.push(...checkInstallation(ctx));
  } catch (error) { errors.push(error.message); }
}

if (errors.length) {
  process.stderr.write(`doctor: FAIL\n- ${errors.join("\n- ")}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`doctor: PASS (${definitions.length} agents, ${skillNames.size} skills${repositoryOnly ? ", repository only" : ""})\n`);
}
