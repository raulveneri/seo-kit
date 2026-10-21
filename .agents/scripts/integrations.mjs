import { existsSync, lstatSync, readFileSync, readdirSync, unlinkSync } from "node:fs";
import path from "node:path";
import { sha256, writeAtomic } from "./lib.mjs";

export const START = "<!-- BEGIN seo-kit managed discovery -->";
export const END = "<!-- END seo-kit managed discovery -->";

export function discoveryBlock(root) {
  return `${START}\n${readFileSync(path.join(root, ".agents/runtime/discovery.md"), "utf8").replaceAll("{{ROOT}}", root.replaceAll("\\", "/")).trim()}\n${END}`;
}

export function getBlock(content) {
  const start = content.indexOf(START);
  const end = content.indexOf(END);
  if (start < 0 && end < 0) return null;
  if (start < 0 || end < start || content.indexOf(START, start + START.length) >= 0 || content.indexOf(END, end + END.length) >= 0) {
    throw new Error("Malformed seo-kit discovery markers. Repair the marked block before retrying");
  }
  return content.slice(start, end + END.length);
}

export function mergeBlock(content, block) {
  const old = getBlock(content);
  return old ? content.replace(old, block) : `${content}${content && !content.endsWith("\n") ? "\n" : ""}\n${block}\n`;
}

function tree(directory, target, output) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const source = path.join(directory, entry.name);
    const destination = path.join(target, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Refusing symlink in release resources: ${source}`);
    if (entry.isDirectory()) tree(source, destination, output);
    else if (entry.isFile()) output.set(destination, { content: readFileSync(source, "utf8"), kind: "file" });
  }
}

export function integrationFiles(root, paths) {
  const output = new Map();
  const skills = path.join(root, ".agents/skills");
  // Copies work on Windows without Developer Mode or symlink privileges.
  tree(skills, paths.sharedSkills, output);
  tree(skills, path.join(paths.claude, "skills"), output);
  // OpenCode also discovers ~/.agents/skills. Avoid duplicate skill catalogs.
  for (const [format, target] of [
    ["claude/agents", path.join(paths.claude, "agents")],
    ["codex/agents", path.join(paths.codex, "agents")],
    ["opencode/agent", path.join(paths.opencodeResources ?? paths.opencode, "agents")],
  ]) tree(path.join(root, ".agents/adapters", format), target, output);
  const codexRules = existsSync(path.join(paths.codex, "AGENTS.override.md"))
    ? "AGENTS.override.md" : "AGENTS.md";
  for (const file of [path.join(paths.claude, "CLAUDE.md"), path.join(paths.codex, codexRules), path.join(paths.opencode, "AGENTS.md")]) {
    output.set(file, { kind: "block", content: discoveryBlock(root) });
  }
  return output;
}

export function assertRegularAncestors(file) {
  let current = file;
  for (;;) {
    try {
      if (lstatSync(current).isSymbolicLink()) throw new Error(`Refusing to write through symlink: ${current}. Remove the old kit's managed links with its setup:remove command, or choose a separate assistant profile.`);
    } catch (error) { if (error.code !== "ENOENT") throw error; }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
}

export function readOptional(file) {
  try { return readFileSync(file, "utf8"); } catch (error) { if (error.code === "ENOENT") return null; throw error; }
}

// Preflight every destination before the first write. Edited managed files are
// conflicts too: an unattended update must never discard a user's changes.
export function planIntegrations(root, paths, previous = { resources: {} }, removing = false) {
  const desired = removing ? new Map() : integrationFiles(root, paths);
  const changes = [];
  const resources = {};
  for (const file of new Set([...Object.keys(previous.resources), ...desired.keys()])) {
    assertRegularAncestors(file);
    const before = readOptional(file);
    const old = previous.resources[file];
    const next = desired.get(file);
    const kind = next?.kind ?? old.kind;
    const installed = kind === "block" ? getBlock(before ?? "") : before;
    if (old && (installed === null || sha256(installed) !== old.hash)) throw new Error(`Local changes conflict with kit update: ${file}`);
    if (!old && installed !== null && (kind === "file" || installed !== next.content)) throw new Error(`Existing resource belongs to another installation: ${file}`);
    let after = null;
    if (next) {
      after = kind === "block" ? mergeBlock(before ?? "", next.content) : next.content;
      resources[file] = { kind, hash: sha256(next.content) };
    } else if (kind === "block") {
      // Preserve every byte outside the managed block.
      after = before.replace(installed, "");
    }
    if (before !== after) changes.push({ file, before, after });
  }
  return { changes, resources };
}

export function applyChanges(changes) {
  for (const { file, after } of changes) {
    assertRegularAncestors(file);
    if (after === null) { if (existsSync(file)) unlinkSync(file); }
    else writeAtomic(file, after, existsSync(file) ? {} : { mode: 0o600 });
  }
}

export function restoreChanges(changes) {
  applyChanges(changes.map(({ file, before }) => ({ file, after: before })));
}
