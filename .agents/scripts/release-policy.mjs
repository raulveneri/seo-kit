// Published stable GitHub releases are the approval record. Never fall back to main.
export function selectApprovedRelease(releases, approverId) {
  if (!Array.isArray(releases) || !Number.isSafeInteger(approverId) || approverId <= 0) throw new Error("Invalid release policy or API response");
  const candidates = releases.filter((release) => release && release.draft === false && release.prerelease === false && release.author?.id === approverId && typeof release.published_at === "string" && Number.isFinite(Date.parse(release.published_at)));
  candidates.sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at) || b.id - a.id);
  const release = candidates[0];
  if (!release) throw new Error("No owner-approved stable release is published. Main and unapproved tags will not be installed");
  if (release.immutable !== true) throw new Error("Owner-approved release must be immutable. Enable release immutability before publishing");
  if (!Number.isSafeInteger(release.id) || release.id <= 0 || !/^v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$/.test(release.tag_name) || !/^[a-f0-9]{40,64}$/.test(release.target_commitish)) {
    throw new Error("Approved release must have a vMAJOR.MINOR.PATCH tag and a full target commit SHA. Publish it with --target <full-sha>");
  }
  return { id: release.id, tag: release.tag_name, commit: release.target_commitish, approverId, publishedAt: release.published_at };
}

export function approvedRelease(ctx, config) {
  if (config.updateChannel !== "owner-approved-releases") throw new Error("Unsupported update channel. Refusing branch fallback");
  // One bounded page. If there is no approved candidate, fail closed.
  const result = ctx.execute("gh", ["api", "--hostname", "github.com", `repos/${config.repository}/releases?per_page=100`, "--header", "Accept: application/vnd.github+json"], {
    cwd: ctx.base, timeout: 30_000,
    env: { ...process.env, ...ctx.env, GH_HOST: "github.com", GH_PROMPT_DISABLED: "1", GH_PAGER: "cat" },
  });
  return selectApprovedRelease(JSON.parse(result.stdout), config.releaseApprover.id);
}
