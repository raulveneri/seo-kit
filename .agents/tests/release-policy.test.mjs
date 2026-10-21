import assert from "node:assert/strict";
import test from "node:test";
import { approvedRelease, selectApprovedRelease } from "../scripts/release-policy.mjs";

const owner = 1234;
const stable = { id: 10, tag_name: "v1.0.0", target_commitish: "a".repeat(40), draft: false, prerelease: false, immutable: true, author: { id: owner }, published_at: "2026-10-20T10:00:00Z" };

test("release policy excludes drafts, prereleases and releases by other authors", () => {
  const selected = selectApprovedRelease([
    { ...stable, id: 11, draft: true }, { ...stable, id: 12, prerelease: true },
    { ...stable, id: 13, author: { id: 9999 } }, stable,
  ], owner);
  assert.equal(selected.id, 10);
  assert.equal(selected.commit, stable.target_commitish);
  assert.throws(() => selectApprovedRelease([], owner), /No owner-approved/);
  assert.throws(() => selectApprovedRelease([{ ...stable, author: { id: 9999 } }], owner), /No owner-approved/);
  assert.throws(() => selectApprovedRelease([{ ...stable, immutable: false }], owner), /must be immutable/);
});

test("latest published owner approval must pin a full commit and a safe stable tag", () => {
  const newer = { ...stable, id: 20, tag_name: "v1.1.0", published_at: "2026-10-20T11:00:00Z" };
  assert.equal(selectApprovedRelease([stable, newer], owner).id, 20);
  for (const changes of [{ target_commitish: "main" }, { target_commitish: "abc123" }, { tag_name: "--upload-pack=evil" }, { tag_name: "v1.0.0-beta" }]) {
    assert.throws(() => selectApprovedRelease([stable, { ...newer, ...changes }], owner), /full target commit SHA/);
  }
  assert.throws(() => selectApprovedRelease({}, owner), /Invalid/);
});

test("release lookup is bounded to GitHub and fails closed on unavailable approval", () => {
  let invocation;
  const ctx = { base: "/tmp", env: {}, execute: (command, args, options) => { invocation = { command, args, options }; return { stdout: JSON.stringify([stable]) }; } };
  const config = { repository: "example/kit", updateChannel: "owner-approved-releases", releaseApprover: { id: owner } };
  assert.equal(approvedRelease(ctx, config).id, 10);
  assert.equal(invocation.command, "gh");
  assert.ok(invocation.args.includes("repos/example/kit/releases?per_page=100"));
  assert.equal(invocation.options.env.GH_HOST, "github.com");
  assert.throws(() => approvedRelease(ctx, { ...config, updateChannel: "main" }), /Refusing branch fallback/);
  assert.throws(() => approvedRelease({ ...ctx, execute() { throw new Error("offline"); } }, config), /offline/);
});
