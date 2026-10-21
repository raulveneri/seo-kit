import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { checkPrivateData, privateDataFindings } from "../scripts/check-private-data.mjs";

test("private data patterns catch credentials without exposing values", () => {
  const token = "ghp_" + "a".repeat(36);
  const findings = privateDataFindings("docs/example.md", `Example\n${token}`);
  assert.deepEqual(findings, [{ file: "docs/example.md", line: 2, kind: "credential format" }]);
  assert.equal(JSON.stringify(findings).includes(token), false);
  assert.equal(privateDataFindings("forced/.env.production", "VALUE=anything")[0].kind, "environment file");
  assert.deepEqual(privateDataFindings(".env.example", "VALUE=placeholder"), []);
});

test("identity checks allow documented fixtures, not arbitrary test identities", () => {
  assert.deepEqual(privateDataFindings(".agents/tests/fixture.mjs", '"/home/alice"; "C:\\Users\\Alice"; fixture@example.test'), []);
  const personalEmail = "developer@" + "mail-provider.com";
  const personalHome = "/home/" + "developer";
  assert.equal(privateDataFindings("docs/example.md", personalEmail)[0].kind, "non-example email address");
  assert.equal(privateDataFindings(".agents/tests/fixture.mjs", personalHome)[0].kind, "personal home path");
  assert.equal(privateDataFindings(".agents/runtime/AGENTS.md", "/home/" + "alice")[0].kind, "personal home path");
  assert.deepEqual(privateDataFindings("README.md", "https://github.com/owner/seo-kit"), []);
});

test("local-only files are rejected even with empty or binary content", () => {
  for (const file of [".agents/local/notes.md", ".agents\\local\\notes.md"]) {
    assert.deepEqual(privateDataFindings(file, ""), [{ file, line: 1, kind: "local-only file" }]);
  }
  assert.deepEqual(privateDataFindings("docs/local/notes.md", ""), []);
});

test("worktree scan checks tracked ignored files and new files without reading binary content", (t) => {
  const root = mkdtempSync(path.join(tmpdir(), "seo-kit-private-data-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const args of [["init"], ["config", "core.autocrlf", "false"]]) {
    assert.equal(spawnSync("git", args, { cwd: root }).status, 0);
  }
  writeFileSync(path.join(root, ".gitignore"), ".env\n.agents/local/\n");
  writeFileSync(path.join(root, ".env"), "VALUE=placeholder\n");
  assert.equal(spawnSync("git", ["add", "-f", ".env"], { cwd: root }).status, 0);
  mkdirSync(path.join(root, "docs"));
  writeFileSync(path.join(root, "docs/new.md"), "ghp_" + "b".repeat(36));
  writeFileSync(path.join(root, "binary.bin"), Buffer.from([0, 1, 2]));
  const findings = checkPrivateData(root);
  assert.ok(findings.some((item) => item.file === ".env" && item.kind === "environment file"));
  assert.ok(findings.some((item) => item.file === "docs/new.md" && item.kind === "credential format"));
  assert.equal(findings.some((item) => item.file === "binary.bin"), false);
  mkdirSync(path.join(root, ".agents/local"), { recursive: true });
  writeFileSync(path.join(root, ".agents/local/notes.md"), "Local notes\n");
  assert.equal(checkPrivateData(root).some((item) => item.file.startsWith(".agents/local/")), false);
  assert.equal(spawnSync("git", ["add", "-f", ".agents/local/notes.md"], { cwd: root }).status, 0);
  assert.ok(checkPrivateData(root).some((item) => item.file === ".agents/local/notes.md" && item.kind === "local-only file"));
});
