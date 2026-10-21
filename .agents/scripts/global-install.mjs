import { existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, rmSync, renameSync, statSync, unlinkSync, appendFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { run, sha256, writeAtomic } from "./lib.mjs";
import { platformPaths } from "./platform-paths.mjs";
import { planIntegrations, applyChanges, restoreChanges, readOptional, getBlock, assertRegularAncestors } from "./integrations.mjs";
import { configureUpdates } from "./update-services.mjs";
import { approvedRelease } from "./release-policy.mjs";

const config = JSON.parse(readFileSync(new URL("../seo-kit.json", import.meta.url), "utf8"));
if (!/^[\w.-]+\/[\w.-]+$/.test(config.repository) || !/^[\w][\w./-]*$/.test(config.defaultBranch)) throw new Error("Invalid upstream configuration");
const REPOSITORY = `https://github.com/${config.repository}.git`;
const BRANCH = config.defaultBranch;
if (config.updateChannel !== "owner-approved-releases" || !Number.isSafeInteger(config.releaseApprover?.id) || config.releaseApprover.id <= 0) throw new Error("Invalid release approval policy");

export function installation(options = {}) {
  const home = options.home ?? homedir();
  const platform = options.platform ?? process.platform;
  const env = options.env ?? process.env;
  const selectedPaths = options.paths ?? platformPaths({ home, platform, env });
  const base = options.base ?? env.SEO_KIT_MANAGED_BASE ?? selectedPaths.base;
  if (!(platform === "win32" ? path.win32 : path.posix).isAbsolute(base)) throw new Error("Managed base must be absolute");
  const paths = { ...selectedPaths, base };
  return { home, platform, env, execute: options.execute ?? run, ...options, paths, base };
}

function statePath(ctx) { return path.join(ctx.base, "state", "installation.json"); }
function assertRelease(ctx, root) {
  if (path.dirname(root) !== path.join(ctx.base, "releases") || !/^[a-f0-9]{40,64}$/.test(path.basename(root))) throw new Error(`Invalid managed release path: ${root}`);
}
export function readInstallation(ctx) {
  const content = readOptional(statePath(ctx));
  if (!content) return null;
  const value = JSON.parse(content);
  if (value.schema !== 1) throw new Error("Unsupported installation state version");
  assertRelease(ctx, value.root);
  return value;
}

function event(ctx, message, error = false) {
  const line = `${new Date().toISOString()} ${message}\n`;
  const file = path.join(ctx.base, "state", "updates.log");
  if (existsSync(file) && statSync(file).size > 1024 * 1024) {
    rmSync(`${file}.1`, { force: true });
    renameSync(file, `${file}.1`);
  }
  appendFileSync(file, line, { mode: 0o600 });
  (error ? process.stderr : process.stdout).write(line);
}

export function withInstallationLock(ctx, action) {
  assertRegularAncestors(path.join(ctx.base, "state/installation.json"));
  mkdirSync(path.join(ctx.base, "state"), { recursive: true, mode: 0o700 });
  const lock = path.join(ctx.base, "state", "lock");
  try { mkdirSync(lock); }
  catch (error) {
    if (error.code !== "EEXIST") throw error;
    const owner = readOptional(path.join(lock, "pid"));
    let alive = true;
    if (owner && /^\d+$/.test(owner.trim())) {
      try { process.kill(Number(owner), 0); } catch (failure) { if (failure.code === "ESRCH") alive = false; }
    } else alive = Date.now() - statSync(lock).mtimeMs < 10 * 60_000;
    if (alive) throw new Error("Another SEO Kit installation/update is running");
    rmSync(lock, { recursive: true });
    mkdirSync(lock);
  }
  writeAtomic(path.join(lock, "pid"), String(process.pid), { mode: 0o600 });
  try { recover(ctx); return action(); }
  finally { rmSync(lock, { recursive: true, force: true }); }
}

function recover(ctx) {
  const file = path.join(ctx.base, "state", "transaction.json");
  const saved = readOptional(file);
  if (!saved) return;
  const transaction = JSON.parse(saved);
  restoreChanges(transaction.changes);
  if (transaction.before === null) rmSync(statePath(ctx), { force: true });
  else writeAtomic(statePath(ctx), transaction.before, { mode: 0o600 });
  unlinkSync(file);
  event(ctx, "Recovered interrupted integration update. Previous version restored");
}

export function verifyRelease(root, execute = run) {
  execute(process.execPath, [path.join(root, ".agents/scripts/build-adapters.mjs")], { cwd: root });
  execute(process.execPath, [path.join(root, ".agents/scripts/doctor.mjs"), "--repository-only"], { cwd: root });
  const dirty = execute("git", ["status", "--porcelain", "--untracked-files=all"], { cwd: root }).stdout.trim();
  if (dirty) throw new Error(`Release validation changed tracked/generated resources: ${dirty}`);
}

function git(ctx, args, root) {
  return ctx.execute("git", args, {
    cwd: root ?? ctx.base, timeout: 120_000,
    env: { ...process.env, ...ctx.env, GIT_TERMINAL_PROMPT: "0", GCM_INTERACTIVE: "Never" },
  });
}
function sameRepository(a, b) {
  if (a === b) return true;
  if (process.platform !== "win32" || !path.isAbsolute(a) || !path.isAbsolute(b)) return false;
  return path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase();
}
function prepareRelease(ctx, current) {
  const releases = path.join(ctx.base, "releases");
  mkdirSync(releases, { recursive: true });
  const repository = current?.repository ?? ctx.repository ?? REPOSITORY;
  if (current) {
    if (git(ctx, ["rev-parse", "HEAD"], current.root).stdout.trim() !== current.commit) throw new Error("Managed release HEAD changed. Update stopped");
    if (git(ctx, ["status", "--porcelain", "--untracked-files=all"], current.root).stdout.trim()) throw new Error("Managed release contains local edits. Update stopped without discarding them");
    if (!sameRepository(git(ctx, ["remote", "get-url", "origin"], current.root).stdout.trim(), repository)) throw new Error("Managed release origin changed. Update stopped");
  }
  const approval = (ctx.resolveRelease ?? approvedRelease)(ctx, config);
  // Validate injected providers too. Only tests supply a different resolver.
  if (!Number.isSafeInteger(approval.id) || approval.id <= 0 || !Number.isFinite(Date.parse(approval.publishedAt)) || !/^[a-f0-9]{40,64}$/.test(approval.commit) || !/^v\d+\.\d+\.\d+$/.test(approval.tag) || approval.approverId !== config.releaseApprover.id) throw new Error("Invalid release approval");
  if (current?.approval && (Date.parse(approval.publishedAt) < Date.parse(current.approval.publishedAt) || (approval.publishedAt === current.approval.publishedAt && approval.id < current.approval.id))) throw new Error("Approved release is older than the installed approval. Retaining installed version");
  if (current?.approval?.id === approval.id && (current.approval.commit !== approval.commit || current.approval.tag !== approval.tag || current.approval.publishedAt !== approval.publishedAt)) throw new Error("Published approval changed. Retaining installed version");
  if (current) {
    git(ctx, ["fetch", "--no-tags", "origin", `refs/tags/${approval.tag}`], current.root);
    const target = git(ctx, ["rev-parse", "FETCH_HEAD^{commit}"], current.root).stdout.trim();
    if (target !== approval.commit) throw new Error("Release tag and approved commit disagree. Retaining installed version");
    if (target === current.commit) return { root: current.root, approval };
    if (ctx.execute("git", ["merge-base", "--is-ancestor", current.commit, target], { cwd: current.root, allowFailure: true }).status !== 0) throw new Error("Upstream history diverged. Retaining the installed version");
  }
  const stage = path.join(releases, `.staging-${process.pid}`);
  rmSync(stage, { recursive: true, force: true });
  try {
    if (current) {
      git(ctx, ["clone", "--no-hardlinks", "--no-checkout", "--", current.root, stage]);
      git(ctx, ["remote", "set-url", "origin", repository], stage);
      git(ctx, ["fetch", "--no-tags", "origin", `refs/tags/${approval.tag}`], stage);
      if (git(ctx, ["rev-parse", "FETCH_HEAD^{commit}"], stage).stdout.trim() !== approval.commit) throw new Error("Release tag and approved commit disagree");
      git(ctx, ["checkout", "--detach", approval.commit], stage);
    } else {
      git(ctx, ["clone", "--no-checkout", "--no-tags", "--", repository, stage]);
      git(ctx, ["fetch", "--no-tags", "origin", `refs/tags/${approval.tag}`], stage);
      if (git(ctx, ["rev-parse", "FETCH_HEAD^{commit}"], stage).stdout.trim() !== approval.commit) throw new Error("Release tag and approved commit disagree");
      git(ctx, ["checkout", "--detach", approval.commit], stage);
    }
    const commit = git(ctx, ["rev-parse", "HEAD"], stage).stdout.trim();
    if (!/^[a-f0-9]{40,64}$/.test(commit)) throw new Error("Invalid release commit");
    (ctx.verify ?? verifyRelease)(stage, ctx.execute);
    const destination = path.join(releases, commit);
    if (existsSync(destination)) {
      (ctx.verify ?? verifyRelease)(destination, ctx.execute);
      if (git(ctx, ["rev-parse", "HEAD"], destination).stdout.trim() !== commit) throw new Error("Release directory and commit disagree");
    } else renameSync(stage, destination);
    return { root: destination, approval };
  } finally { rmSync(stage, { recursive: true, force: true }); }
}

export function activate(ctx, root, previous, overrides = {}) {
  assertRelease(ctx, root);
  const paths = { ...(previous?.paths ?? ctx.paths), base: ctx.base };
  const plan = planIntegrations(root, paths, previous ?? { resources: {} });
  const next = {
    schema: 1, repository: previous?.repository ?? ctx.repository ?? REPOSITORY,
    commit: path.basename(root), root, previousRoot: previous?.root === root ? previous.previousRoot : previous?.root ?? null,
    previousApproval: previous?.root === root ? previous.previousApproval ?? null : previous?.approval ?? null,
    paths, resources: plan.resources, scheduler: previous?.scheduler ?? null,
    installedAt: previous?.installedAt ?? new Date().toISOString(), updatedAt: new Date().toISOString(), ...overrides,
  };
  const journal = path.join(ctx.base, "state", "transaction.json");
  writeAtomic(journal, JSON.stringify({ before: readOptional(statePath(ctx)), changes: plan.changes }), { mode: 0o600 });
  try {
    applyChanges(plan.changes);
    writeAtomic(statePath(ctx), `${JSON.stringify(next, null, 2)}\n`, { mode: 0o600 });
    unlinkSync(journal);
  } catch (error) { recover(ctx); throw error; }
  return next;
}

function writeLauncher(ctx) {
  const content = `// GENERATED BY seo-kit. Stable entry point, independent of the active release.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const base = path.dirname(fileURLToPath(import.meta.url));
const state = JSON.parse(readFileSync(path.join(base, 'state/installation.json'), 'utf8'));
if (path.dirname(state.root) !== path.join(base, 'releases') || !/^[a-f0-9]{40,64}$/.test(path.basename(state.root))) throw new Error('Invalid managed release');
const args = process.argv.slice(2);
const action = args.shift() ?? 'status';
const result = spawnSync(process.execPath, [path.join(state.root, '.agents/scripts/setup.mjs'), action, ...args], { stdio: 'inherit', env: { ...process.env, SEO_KIT_MANAGED_BASE: base } });
if (result.error) process.stderr.write(result.error.message + '\\n');
process.exitCode = result.status ?? 1;
`;
  const file = path.join(ctx.base, "seo-kit.mjs");
  if (readOptional(file) && !readOptional(file).includes("GENERATED BY seo-kit")) throw new Error(`Foreign launcher: ${file}`);
  writeAtomic(file, content);
}

function cleanReleases(ctx, current) {
  const keep = new Set([current.root, current.previousRoot]);
  for (const entry of readdirSync(path.join(ctx.base, "releases"), { withFileTypes: true })) {
    const root = path.join(ctx.base, "releases", entry.name);
    if (!entry.isDirectory() || !/^[a-f0-9]{40,64}$/.test(entry.name) || keep.has(root)) continue;
    try {
      if (!git(ctx, ["status", "--porcelain", "--untracked-files=all", "--ignored"], root).stdout.trim()) rmSync(root, { recursive: true });
    } catch (error) { event(ctx, `Old release retained. Cleanup could not complete: ${error.message}`); }
  }
}

export function installGlobal(options = {}) {
  const ctx = installation(options);
  if (options.dryRun) {
    process.stdout.write(`install: clone an owner-approved stable release from ${REPOSITORY} into ${ctx.base}. Never install ${BRANCH} directly\n`);
    process.stdout.write(`discovery: shared skills ${ctx.paths.sharedSkills}, Claude ${ctx.paths.claude}, Codex ${ctx.paths.codex}, OpenCode ${ctx.paths.opencode}\n`);
    process.stdout.write(`updates: ${options.noServices ? "disabled by request" : `hourly and at login/startup using the ${ctx.platform} user scheduler`}\n`);
    return;
  }
  return withInstallationLock(ctx, () => {
    const previous = readInstallation(ctx);
    const { root, approval } = prepareRelease(ctx, previous);
    writeLauncher(ctx);
    let state = activate(ctx, root, previous, { approval });
    if (!options.noServices || previous?.scheduler || previous?.schedulerError) {
      try {
        const scheduler = configureUpdates({ ...ctx, paths: state.paths, scheduler: previous?.scheduler, remove: !!options.noServices });
        state = { ...state, scheduler: options.noServices ? null : scheduler, schedulerError: null };
        writeAtomic(statePath(ctx), `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
      } catch (error) {
        writeAtomic(statePath(ctx), `${JSON.stringify({ ...state, schedulerError: error.message }, null, 2)}\n`, { mode: 0o600 });
        event(ctx, `Scheduler setup failed. Resources installed, automatic updates NOT confirmed: ${error.message}`, true);
        throw error;
      }
    }
    event(ctx, `Installed ${state.commit} at ${root}. Updates: ${state.scheduler ?? "disabled"}`);
    cleanReleases(ctx, state);
    return state;
  });
}

export function syncGlobal(options = {}) {
  const ctx = installation(options);
  return withInstallationLock(ctx, () => {
    try {
      const current = readInstallation(ctx);
      if (!current) throw new Error("SEO Kit is not installed globally. Run npm run setup first");
      const { root, approval } = prepareRelease(ctx, current);
      if (root === current.root) {
        const errors = checkInstallation(ctx, current);
        if (errors.length) throw new Error(errors.join(". "));
        if (JSON.stringify(current.approval) !== JSON.stringify(approval)) writeAtomic(statePath(ctx), `${JSON.stringify({ ...current, approval, updatedAt: new Date().toISOString() }, null, 2)}\n`, { mode: 0o600 });
        event(ctx, `Already current: ${current.commit}`);
        return current;
      }
      const next = activate(ctx, root, current, { approval });
      event(ctx, `Updated ${current.commit} -> ${next.commit}`);
      cleanReleases(ctx, next);
      return next;
    } catch (error) { event(ctx, `Update failed. Retaining installed version: ${error.message}`, true); throw error; }
  });
}

export function rollbackGlobal(options = {}) {
  const ctx = installation(options);
  return withInstallationLock(ctx, () => {
    const current = readInstallation(ctx);
    if (!current?.previousRoot) throw new Error("No previous release is available");
    assertRelease(ctx, current.previousRoot);
    if (!current.previousApproval || current.previousApproval.commit !== path.basename(current.previousRoot) || current.previousApproval.approverId !== config.releaseApprover.id) throw new Error("Previous release has no matching owner approval. Rollback refused");
    (ctx.verify ?? verifyRelease)(current.previousRoot, ctx.execute);
    if (current.scheduler || current.schedulerError) configureUpdates({ ...ctx, paths: current.paths, scheduler: current.scheduler, remove: true });
    const next = activate(ctx, current.previousRoot, current, { scheduler: null, schedulerError: null, approval: current.previousApproval });
    event(ctx, `Rolled back to ${next.commit}. Automatic updates disabled until setup is rerun`);
    return next;
  });
}

export function checkInstallation(ctx, state = readInstallation(ctx)) {
  if (!state) return ["SEO Kit is not installed globally. Run npm run setup"];
  const errors = [];
  if (!existsSync(state.root)) errors.push(`Missing active release: ${state.root}`);
  for (const [file, resource] of Object.entries(state.resources)) {
    try {
      assertRegularAncestors(file);
      const content = readOptional(file);
      const actual = resource.kind === "block" ? getBlock(content ?? "") : content;
      if (actual === null || sha256(actual) !== resource.hash) errors.push(`Missing or modified integration: ${file}`);
    } catch (error) { errors.push(error.message); }
  }
  return errors;
}

function assertRemovalDirectory(ctx) {
  // Never recursively delete a profile, project or unrecognized directory.
  const allowed = new Set(["releases", "state", "seo-kit.mjs"]);
  for (const entry of readdirSync(ctx.base)) {
    if (!allowed.has(entry)) throw new Error(`Unrecognized file in managed installation. Removal stopped: ${path.join(ctx.base, entry)}`);
  }
  const launcher = path.join(ctx.base, "seo-kit.mjs");
  assertRegularAncestors(launcher);
  if (!readOptional(launcher)?.includes("GENERATED BY seo-kit")) throw new Error(`Foreign or missing launcher: ${launcher}`);
  const releases = path.join(ctx.base, "releases");
  assertRegularAncestors(path.join(releases, ".removal-check"));
  for (const entry of readdirSync(releases)) {
    const root = path.join(releases, entry);
    if (!/^[a-f0-9]{40,64}$/.test(entry)) throw new Error(`Unrecognized or incomplete release. Removal stopped: ${root}`);
    assertRegularAncestors(path.join(root, ".git"));
    // Check every retained release, not only the active integration copies.
    // Include ignored files: they can contain personal work too.
    const top = git(ctx, ["rev-parse", "--show-toplevel"], root).stdout.trim();
    // Git may expand a Windows 8.3 path (RUNNER~1) that Node retained.
    // Compare actual directory identities without weakening the symlink preflight above.
    if (!sameRepository(realpathSync.native(top), realpathSync.native(root)) || git(ctx, ["rev-parse", "HEAD"], root).stdout.trim() !== entry) {
      throw new Error(`Managed release identity changed. Removal stopped: ${root}`);
    }
    const changes = git(ctx, ["status", "--porcelain", "--untracked-files=all", "--ignored"], root).stdout.trim();
    if (changes) throw new Error(`Local changes or extra files in managed release. Removal stopped: ${root}. Preserve or resolve them before retrying.`);
  }
  const state = path.join(ctx.base, "state");
  const stateFiles = new Set(["installation.json", "transaction.json", "lock", "updates.log", "updates.log.1", "scheduler.log", "scheduler.error.log", "scheduled-task.ps1"]);
  for (const entry of readdirSync(state)) {
    if (!stateFiles.has(entry)) throw new Error(`Unrecognized state file. Removal stopped: ${path.join(state, entry)}`);
  }
}

export function removeGlobal(options = {}) {
  const ctx = installation(options);
  return withInstallationLock(ctx, () => {
    const current = readInstallation(ctx);
    if (!current) throw new Error("No managed installation found");
    assertRemovalDirectory(ctx);
    const plan = planIntegrations(current.root, current.paths, current, true);
    if (current.scheduler || current.schedulerError) configureUpdates({ ...ctx, paths: current.paths, scheduler: current.scheduler, remove: true });
    const journal = path.join(ctx.base, "state/transaction.json");
    writeAtomic(journal, JSON.stringify({ before: readOptional(statePath(ctx)), changes: plan.changes }), { mode: 0o600 });
    try {
      applyChanges(plan.changes);
      rmSync(statePath(ctx));
      unlinkSync(journal);
    } catch (error) { recover(ctx); throw error; }
    // All modules are already loaded. Move our working directory outside the
    // installation so Windows can also remove the executing release directory.
    const relative = path.relative(ctx.base, process.cwd());
    if (relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative))) process.chdir(path.dirname(ctx.base));
    rmSync(ctx.base, { recursive: true });
    process.stdout.write("Removed managed integrations, automatic updates, releases, logs and installation directory\n");
  });
}
