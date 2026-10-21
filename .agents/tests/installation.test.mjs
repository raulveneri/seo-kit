import assert from "node:assert/strict";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, renameSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { platformPaths } from "../scripts/platform-paths.mjs";
import { installation, installGlobal, syncGlobal, rollbackGlobal, removeGlobal, readInstallation, checkInstallation, withInstallationLock } from "../scripts/global-install.mjs";
import { integrationFiles, planIntegrations, getBlock, START, END } from "../scripts/integrations.mjs";
import { configureUpdates, windowsRegistration } from "../scripts/update-services.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
function temporary(t) {
  const directory = mkdtempSync(path.join(realpathSync(tmpdir()), "seo kit unicode-é-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  return directory;
}
function execute(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: options.cwd, encoding: "utf8", input: options.input, timeout: 120_000 });
  if (result.status !== 0 && !options.allowFailure) throw new Error(`${command} ${args.join(" ")}: ${result.error?.message ?? result.stderr}`);
  return result;
}
function git(directory, ...args) { return execute("git", args, { cwd: directory }).stdout.trim(); }
function fixture(t) {
  const directory = temporary(t);
  const repository = path.join(directory, "upstream");
  const home = path.join(directory, "home");
  mkdirSync(repository);
  mkdirSync(home);
  cpSync(path.join(root, ".agents"), path.join(repository, ".agents"), { recursive: true, filter: (file) => !file.includes("__pycache__") && !file.endsWith(".pyc") && !path.relative(root, file).startsWith(`.agents${path.sep}local`) });
  for (const file of [".gitattributes", "AGENTS.md", "package.json"]) cpSync(path.join(root, file), path.join(repository, file));
  git(repository, "init", "-b", "main");
  git(repository, "config", "user.email", "fixture@example.test");
  git(repository, "config", "user.name", "Fixture");
  git(repository, "add", ".");
  git(repository, "commit", "-m", "initial");
  const approvals = new Map();
  const resolveRelease = (_ctx, policy) => {
    const commit = git(repository, "rev-parse", "HEAD");
    if (!approvals.has(commit)) {
      const id = approvals.size + 1;
      const tag = `v0.0.${id}`;
      git(repository, "tag", tag, commit);
      approvals.set(commit, { id, tag, commit, approverId: policy.releaseApprover.id, publishedAt: new Date(id * 1000).toISOString() });
    }
    return approvals.get(commit);
  };
  const options = { home, env: {}, repository, noServices: true, execute, resolveRelease };
  return { directory, repository, home, options, ctx: installation(options) };
}
function advance(repository, filename = ".agents/runtime/discovery.md", text = "\nAdditional routing guidance.\n") {
  writeFileSync(path.join(repository, filename), readFileSync(path.join(repository, filename), "utf8") + text);
  git(repository, "add", ".");
  git(repository, "commit", "-m", "update");
  return git(repository, "rev-parse", "HEAD");
}

test("native global paths cover Windows, macOS, XDG Linux and portable fallback", () => {
  const home = String.raw`C:\Users\O'Neil`;
  const expected = path.win32.join(home, ".local", "share", "ai-kits", "seo-kit");
  for (const LOCALAPPDATA of [undefined, String.raw`D:\User Data`, path.win32.join(home, "AppData", "Local", "Packages", "Example.Desktop", "LocalCache", "Local")]) {
    const paths = platformPaths({ platform: "win32", home, env: { LOCALAPPDATA, XDG_DATA_HOME: String.raw`D:\Other Data`, CODEX_HOME: String.raw`D:\Profiles\Codex` } });
    assert.equal(paths.base, expected);
    assert.equal(paths.codex, String.raw`D:\Profiles\Codex`);
    assert.equal(paths.sharedSkills, path.win32.join(home, ".agents", "skills"));
  }
  assert.equal(platformPaths({ platform: "darwin", home: "/Users/alice", env: {} }).base, "/Users/alice/Library/Application Support/ai-kits/seo-kit");
  assert.equal(platformPaths({ platform: "linux", home: "/home/alice", env: { XDG_DATA_HOME: "/data", CODEX_HOME: "/profiles/codex" } }).base, "/data/ai-kits/seo-kit");
  assert.equal(platformPaths({ platform: "linux", home: "/home/alice", env: { XDG_DATA_HOME: "relative" } }).base, "/home/alice/.local/share/ai-kits/seo-kit");
  assert.equal(platformPaths({ platform: "freebsd", home: "/home/alice", env: {} }).base, "/home/alice/.local/share/ai-kits/seo-kit");
});

test("dry-run has no filesystem, Git or scheduler side effects", (t) => {
  const directory = temporary(t);
  const home = path.join(directory, "absent");
  installGlobal({ home, env: {}, dryRun: true, execute() { throw new Error("must not execute"); } });
  assert.equal(existsSync(home), false);
});

test("an explicit managed base stays consistent across installation and maintenance", (t) => {
  const { options, home, repository } = fixture(t);
  const base = path.join(home, "managed data", "seo-kit");
  const selected = { ...options, env: { SEO_KIT_MANAGED_BASE: base } };
  const ctx = installation(selected);
  assert.equal(ctx.base, base);
  assert.equal(ctx.paths.base, base);
  assert.throws(() => installation({ ...options, env: { SEO_KIT_MANAGED_BASE: "relative" } }), /must be absolute/);
  const first = installGlobal(selected);
  assert.equal(first.paths.base, base);
  selected.env.CODEX_HOME = path.join(home, "different-codex-profile");
  assert.equal(installGlobal(selected).commit, first.commit);
  const commit = advance(repository);
  const updated = syncGlobal(selected);
  assert.equal(updated.commit, commit);
  assert.deepEqual(updated.paths, first.paths);
  assert.deepEqual(checkInstallation(ctx), []);
  assert.equal(rollbackGlobal(selected).commit, first.commit);
  removeGlobal(selected);
  assert.equal(existsSync(base), false);
});

test("install, repeated setup, update, rollback and uninstall preserve user guidance", (t) => {
  const { options, ctx, repository } = fixture(t);
  mkdirSync(ctx.paths.codex, { recursive: true });
  const instructions = path.join(ctx.paths.codex, "AGENTS.override.md");
  writeFileSync(instructions, "Personal instructions.\n", { mode: 0o600 });
  const otherSkill = path.join(ctx.paths.claude, "skills/personal-skill/SKILL.md");
  mkdirSync(path.dirname(otherSkill), { recursive: true });
  writeFileSync(otherSkill, "Personal skill\n");
  const first = installGlobal(options);
  const launched = execute(process.execPath, [path.join(ctx.base, "seo-kit.mjs"), "status"], { cwd: path.dirname(repository) });
  assert.ok(launched.stdout.includes("setup: PASS"));
  const refused = execute(process.execPath, [path.join(ctx.base, "seo-kit.mjs"), "rollback", "--dry-run"], { cwd: path.dirname(repository), allowFailure: true });
  assert.notEqual(refused.status, 0);
  assert.ok(refused.stderr.includes("No action performed"));
  assert.deepEqual(checkInstallation(ctx), []);
  assert.equal(readInstallation(ctx).commit, first.commit);
  assert.ok(readFileSync(instructions, "utf8").startsWith("Personal instructions.\n"));
  if (process.platform !== "win32") assert.equal(statSync(instructions).mode & 0o777, 0o600);
  assert.ok(getBlock(readFileSync(instructions, "utf8")).includes(first.root.replaceAll("\\", "/")));
  assert.equal(existsSync(path.join(ctx.paths.opencode, "agents/seo-audit.md")), true);
  assert.equal(existsSync(path.join(ctx.paths.sharedSkills, "seo-optimization/SKILL.md")), true);
  const second = installGlobal(options);
  assert.equal(first.commit, second.commit);
  const userText = readFileSync(instructions, "utf8") + "More personal guidance.\n";
  writeFileSync(instructions, userText);
  const commit = advance(repository);
  const updated = syncGlobal(options);
  assert.equal(updated.commit, commit);
  assert.equal(updated.previousRoot, first.root);
  assert.ok(readFileSync(instructions, "utf8").endsWith("More personal guidance.\n"));
  const rolled = rollbackGlobal(options);
  assert.equal(rolled.commit, first.commit);
  assert.equal(rolled.scheduler, null);
  removeGlobal(options);
  assert.equal(readInstallation(ctx), null);
  assert.equal(existsSync(path.join(ctx.paths.sharedSkills, "seo-optimization/SKILL.md")), false);
  const preserved = readFileSync(instructions, "utf8");
  assert.ok(preserved.includes("Personal instructions."));
  assert.ok(preserved.includes("More personal guidance."));
  assert.equal(preserved.includes(START), false);
  assert.equal(existsSync(ctx.base), false);
  assert.equal(readFileSync(otherSkill, "utf8"), "Personal skill\n");
});

test("uninstall launcher previews, protects edits and removes integrations without the source checkout", (t) => {
  const { options, ctx, repository, directory } = fixture(t);
  const project = path.join(directory, "client-project");
  mkdirSync(project);
  const deliverable = path.join(project, "audit.json");
  writeFileSync(deliverable, '{"personal":"client data"}');
  const personalConfig = path.join(ctx.paths.codex, "config.toml");
  mkdirSync(ctx.paths.codex, { recursive: true });
  writeFileSync(personalConfig, 'model = "personal-choice"\n');
  const first = installGlobal(options);
  const launcher = path.join(ctx.base, "seo-kit.mjs");
  const instructions = path.join(ctx.paths.codex, "AGENTS.md");
  const guidance = readFileSync(instructions, "utf8");
  assert.ok(guidance.includes(`node "${first.root.replaceAll("\\", "/")}/../../seo-kit.mjs" uninstall`));
  const skill = path.join(ctx.paths.sharedSkills, "seo-optimization/SKILL.md");
  const original = readFileSync(skill, "utf8");
  rmSync(repository, { recursive: true });
  const run = (...args) => execute(process.execPath, [launcher, "uninstall", ...args], { cwd: path.dirname(repository), allowFailure: true });
  const preview = run("--dry-run");
  assert.equal(preview.status, 0, preview.stderr);
  assert.match(preview.stdout, /would remove/);
  assert.equal(readInstallation(ctx).commit, first.commit);
  assert.equal(readFileSync(instructions, "utf8"), guidance);
  assert.deepEqual(checkInstallation(ctx), []);
  const invalid = run("--no-services");
  assert.notEqual(invalid.status, 0);
  assert.equal(readInstallation(ctx).commit, first.commit);
  writeFileSync(skill, "Personal edits\n");
  const refused = run();
  assert.notEqual(refused.status, 0);
  assert.match(refused.stderr, /Local changes conflict/);
  assert.equal(readFileSync(skill, "utf8"), "Personal edits\n");
  assert.equal(readInstallation(ctx).commit, first.commit);
  writeFileSync(skill, original);
  writeFileSync(path.join(ctx.base, "state/updates.log.1"), "Older logs\n");
  writeFileSync(path.join(ctx.base, "state/scheduler.log"), "Scheduler logs\n");
  const removed = run();
  assert.equal(removed.status, 0, removed.stderr);
  assert.match(removed.stdout, /uninstall: PASS/);
  assert.equal(readInstallation(ctx), null);
  assert.equal(existsSync(skill), false);
  assert.equal(readFileSync(instructions, "utf8").includes(START), false);
  assert.equal(existsSync(ctx.base), false);
  assert.equal(existsSync(path.join(ctx.base, "state/updates.log")), false);
  assert.equal(readFileSync(deliverable, "utf8"), '{"personal":"client data"}');
  assert.equal(readFileSync(personalConfig, "utf8"), 'model = "personal-choice"\n');
});

test("uninstall refuses unrecognized files before changing integrations", (t) => {
  const { options, ctx } = fixture(t);
  const first = installGlobal(options);
  for (const relative of ["personal.txt", "state/personal.json", "releases/personal-project"]) {
    const file = path.join(ctx.base, relative);
    writeFileSync(file, "Personal content\n");
    assert.throws(() => removeGlobal(options), /Unrecognized/);
    assert.equal(readFileSync(file, "utf8"), "Personal content\n");
    assert.equal(readInstallation(ctx).commit, first.commit);
    assert.deepEqual(checkInstallation(ctx), []);
    rmSync(file);
  }
  removeGlobal(options);
  assert.equal(existsSync(ctx.base), false);
});

test("uninstall preserves changed, untracked and ignored files in every retained release", (t) => {
  const { options, ctx, repository } = fixture(t);
  writeFileSync(path.join(repository, ".gitignore"), "");
  advance(repository, ".gitignore", "*.private\n");
  const first = installGlobal(options);
  advance(repository);
  const current = syncGlobal(options);
  const instructions = path.join(ctx.paths.codex, "AGENTS.md");
  const guidance = readFileSync(instructions, "utf8");
  for (const root of [first.root, current.root]) {
    for (const name of ["personal.txt", "notes.private", ".agents/runtime/discovery.md"]) {
      const file = path.join(root, name);
      const original = existsSync(file) ? readFileSync(file, "utf8") : null;
      writeFileSync(file, "Personal content to preserve\n");
      assert.throws(() => removeGlobal(options), /Local changes or extra files/);
      assert.equal(readFileSync(file, "utf8"), "Personal content to preserve\n");
      assert.equal(readFileSync(instructions, "utf8"), guidance);
      assert.equal(readInstallation(ctx).commit, current.commit);
      if (original === null) rmSync(file);
      else writeFileSync(file, original);
    }
  }
  const staging = path.join(ctx.base, "releases/.staging-123");
  mkdirSync(staging);
  writeFileSync(path.join(staging, "personal.txt"), "Keep this file\n");
  assert.throws(() => removeGlobal(options), /incomplete release/);
  assert.equal(readFileSync(instructions, "utf8"), guidance);
  assert.equal(readFileSync(path.join(staging, "personal.txt"), "utf8"), "Keep this file\n");
  rmSync(staging, { recursive: true });
  const ignored = path.join(first.root, "notes.private");
  writeFileSync(ignored, "Personal ignored content\n");
  advance(repository);
  const latest = syncGlobal(options);
  assert.equal(readFileSync(ignored, "utf8"), "Personal ignored content\n");
  assert.equal(existsSync(first.root), true, "update cleanup must retain releases containing ignored files");
  assert.throws(() => removeGlobal(options), /Local changes or extra files/);
  assert.equal(readInstallation(ctx).commit, latest.commit);
  rmSync(ignored);
  removeGlobal(options);
  assert.equal(existsSync(ctx.base), false);
});

test("uninstall canonicalizes Git directory aliases and still rejects another directory", (t) => {
  const { options, ctx, directory } = fixture(t);
  const first = installGlobal(options);
  const foreign = path.join(directory, "different-directory");
  mkdirSync(foreign);
  const alias = path.join(directory, "git-directory-alias");
  symlinkSync(first.root, alias, process.platform === "win32" ? "junction" : "dir");
  let reported = foreign;
  const selected = { ...options, execute(command, args, settings) {
    if (command === "git" && args[0] === "rev-parse" && args[1] === "--show-toplevel") return { status: 0, stdout: reported + "\n", stderr: "" };
    return execute(command, args, settings);
  } };
  assert.throws(() => removeGlobal(selected), /identity changed/);
  assert.equal(readInstallation(ctx).commit, first.commit);
  assert.deepEqual(checkInstallation(ctx), []);
  reported = alias;
  removeGlobal(selected);
  assert.equal(existsSync(ctx.base), false);
});

test("invalid candidate and edited resources retain the installed release", (t) => {
  const { options, ctx, repository } = fixture(t);
  const first = installGlobal(options);
  advance(repository, ".agents/scripts/setup.mjs", "\ninvalid syntax !\n");
  assert.throws(() => syncGlobal(options), /syntax|failed|FAIL|Unexpected/i);
  assert.equal(readInstallation(ctx).commit, first.commit);
  assert.deepEqual(checkInstallation(ctx), []);
  git(repository, "revert", "--no-edit", "HEAD");
  const file = path.join(ctx.paths.sharedSkills, "seo-optimization/SKILL.md");
  writeFileSync(file, "local edits\n");
  assert.throws(() => syncGlobal(options), /Local changes conflict/);
  assert.equal(readFileSync(file, "utf8"), "local edits\n");
  assert.equal(readInstallation(ctx).commit, first.commit);
});

test("unapproved main changes, unavailable approvals and moved tags never activate", (t) => {
  const { options, ctx, repository } = fixture(t);
  const first = installGlobal(options);
  const nextCommit = advance(repository);
  const unchanged = syncGlobal({ ...options, resolveRelease: () => first.approval });
  assert.equal(unchanged.commit, first.commit, "advancing main alone is not approval");
  assert.throws(() => syncGlobal({ ...options, resolveRelease() { throw new Error("No owner-approved release"); }, verify() { assert.fail("unapproved code must never execute"); } }), /No owner-approved/);
  const policy = JSON.parse(readFileSync(path.join(root, ".agents/seo-kit.json"), "utf8"));
  const approval = options.resolveRelease(ctx, policy);
  git(repository, "tag", "-f", approval.tag, first.commit);
  assert.throws(() => syncGlobal(options), /tag and approved commit disagree/);
  assert.equal(readInstallation(ctx).commit, first.commit);
  git(repository, "tag", "-f", approval.tag, nextCommit);
  const updated = syncGlobal(options);
  assert.equal(updated.commit, nextCommit);
  assert.equal(updated.approval.id, approval.id);
  assert.throws(() => syncGlobal({ ...options, resolveRelease: () => first.approval }), /older than/);
  const changed = { ...approval, commit: first.commit };
  assert.throws(() => syncGlobal({ ...options, resolveRelease: () => changed }), /approval changed/);
  const stateFile = path.join(ctx.base, "state/installation.json");
  writeFileSync(stateFile, JSON.stringify({ ...updated, previousApproval: null }));
  assert.throws(() => rollbackGlobal(options), /no matching owner approval/);
  assert.equal(readInstallation(ctx).commit, nextCommit);
});

test("network failure, modified managed checkout and rewritten upstream fail safely", (t) => {
  const { options, ctx, repository } = fixture(t);
  const first = installGlobal(options);
  const original = path.join(first.root, ".agents/runtime/discovery.md");
  writeFileSync(original, "local release work\n");
  assert.throws(() => syncGlobal(options), /local edits/);
  git(first.root, "restore", ".");
  const moved = `${repository}-offline`;
  // Make the configured origin unavailable without contacting a public server.
  renameSync(repository, moved);
  assert.throws(() => syncGlobal(options), /git fetch|git rev-parse/);
  renameSync(moved, repository);
  git(repository, "checkout", "--orphan", "new-history");
  git(repository, "add", ".");
  git(repository, "commit", "-m", "rewritten");
  git(repository, "branch", "-M", "main");
  assert.throws(() => syncGlobal(options), /diverged/);
  assert.equal(readInstallation(ctx).commit, first.commit);
});

test("foreign skill files and malformed discovery blocks are never overwritten", (t) => {
  const directory = temporary(t);
  const paths = platformPaths({ home: directory, env: {} });
  const files = integrationFiles(root, paths);
  const target = [...files.keys()].find((file) => file.endsWith("seo-optimization/SKILL.md".replaceAll("/", path.sep)));
  mkdirSync(path.dirname(target), { recursive: true });
  writeFileSync(target, "foreign skill");
  assert.throws(() => planIntegrations(root, paths), /belongs to another/);
  assert.equal(readFileSync(target, "utf8"), "foreign skill");
  assert.throws(() => getBlock(`${START}\nbroken`), /Malformed/);
  assert.throws(() => getBlock(`${END}\n${START}`), /Malformed/);
});

test("legacy directory links cannot redirect installer writes into another checkout", { skip: process.platform === "win32" }, (t) => {
  const directory = temporary(t);
  const paths = platformPaths({ home: directory, env: {} });
  mkdirSync(path.dirname(paths.sharedSkills), { recursive: true });
  const foreign = path.join(directory, "foreign");
  mkdirSync(foreign);
  symlinkSync(foreign, paths.sharedSkills, "dir");
  assert.throws(() => planIntegrations(root, paths), /symlink/);
  assert.deepEqual(checkInstallation(installation({ home: directory, env: {} }), null), ["SEO Kit is not installed globally. Run npm run setup"]);
});

test("lock rejects concurrent updates and journal recovers interrupted writes", (t) => {
  const directory = temporary(t);
  const ctx = installation({ home: directory, env: {} });
  withInstallationLock(ctx, () => {
    assert.throws(() => withInstallationLock(ctx, () => {}), /Another SEO Kit/);
  });
  const file = path.join(directory, "integration.md");
  writeFileSync(file, "partial write");
  writeFileSync(path.join(ctx.base, "state/transaction.json"), JSON.stringify({ before: null, changes: [{ file, before: "original", after: "partial write" }] }));
  withInstallationLock(ctx, () => assert.equal(readFileSync(file, "utf8"), "original"));
  assert.equal(existsSync(path.join(ctx.base, "state/transaction.json")), false);
});

test("scheduler adapters cover Windows, macOS, Linux and cron without altering host tasks", (t) => {
  const directory = temporary(t);
  for (const platform of ["win32", "darwin", "linux", "freebsd"]) {
    // Use host-native temporary paths. Platform selection tests the scheduler,
    // while the path table above separately tests native Windows path rules.
    const base = path.join(directory, platform);
    mkdirSync(path.join(base, "state"), { recursive: true });
    const calls = [];
    const executeMock = (command, args, options) => {
      calls.push({ command, args, options });
      return { status: 0, stdout: command === "crontab" && args[0] === "-l" ? "# user task\n5 * * * * echo hello\n" : "", stderr: "" };
    };
    const paths = { config: path.join(base, "config") };
    const scheduler = configureUpdates({ base, paths, home: base, platform, env: { PATH: "/bin:/path with spaces" }, execute: executeMock });
    assert.equal(scheduler, { win32: "windows-task", darwin: "launchd", linux: "systemd", freebsd: "cron" }[platform]);
    if (platform === "win32") {
      const file = path.join(base, "state/scheduled-task.ps1");
      const script = readFileSync(file, "utf8");
      assert.ok(script.includes("-AtLogOn"));
      assert.ok(script.includes("-RepetitionInterval"));
      assert.ok(script.includes("-RunLevel Limited"));
      assert.equal(script.charCodeAt(0), 0xFEFF);
      if (process.platform === "win32") {
        const source = `$parseTokens = $null; $parseErrors = $null; [System.Management.Automation.Language.Parser]::ParseFile('${file.replaceAll("'", "''")}', [ref]$parseTokens, [ref]$parseErrors) | Out-Null; if ($parseErrors.Count) { throw ($parseErrors | Out-String) }`;
        execute("powershell.exe", ["-NoProfile", "-NonInteractive", "-EncodedCommand", Buffer.from(source, "utf16le").toString("base64")]);
      }
    }
    if (platform === "darwin") {
      const file = path.join(base, "Library/LaunchAgents/com.seo-kit.sync.plist");
      assert.ok(readFileSync(file, "utf8").includes("<integer>3600</integer>"));
      if (process.platform === "darwin") execute("plutil", ["-lint", "--", file]);
    }
    if (platform === "linux") assert.ok(readFileSync(path.join(paths.config, "systemd/user/seo-kit-sync.timer"), "utf8").includes("OnUnitActiveSec=1h"));
    if (platform === "freebsd") assert.ok(calls.at(-1).options.input.startsWith("# user task\n5 * * * * echo hello\n"));
    configureUpdates({ base, paths, home: base, platform, env: {}, execute: executeMock, remove: true });
  }
  const script = windowsRegistration("C:\\Users\\O'Neil\\SEO Kit", "C:\\Program Files\\nodejs\\node.exe");
  assert.ok(script.includes("O''Neil"));
});

test("missing scheduler fails explicitly and foreign services are preserved", (t) => {
  const directory = temporary(t);
  const paths = { config: directory };
  const options = { base: directory, paths, home: directory, platform: "linux", env: {}, execute: () => ({ status: 1, stderr: "not available" }) };
  assert.throws(() => configureUpdates(options), /No usable user scheduler/);
  mkdirSync(path.join(directory, "systemd/user"), { recursive: true });
  const file = path.join(directory, "systemd/user/seo-kit-sync.service");
  writeFileSync(file, "foreign service");
  assert.throws(() => configureUpdates({ ...options, execute: () => ({ status: 0 }) }), /Foreign/);
  assert.equal(readFileSync(file, "utf8"), "foreign service");
});
