import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const script = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../scripts/audit.py");
const origin = "https://example.org";

function site() {
  const root = mkdtempSync(path.join(tmpdir(), "seo-kit-audit-"));
  mkdirSync(path.join(root, "about"));
  writeFileSync(path.join(root, "index.html"), `<!doctype html><html lang="en"><head><title>Home | Example</title><meta name="description" content="An example home page."><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="canonical" href="${origin}/"></head><body><h1>Home</h1><a href="/about/">About the organization</a></body></html>`);
  writeFileSync(path.join(root, "about/index.html"), `<!doctype html><html lang="en"><head><title>About | Example</title><meta name="description" content="About this example organization."><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="canonical" href="${origin}/about/"></head><body><h1>About</h1><a href="/">Home</a><img src="/logo.png" alt="Example logo"></body></html>`);
  writeFileSync(path.join(root, "robots.txt"), `User-agent: *\nAllow: /\nSitemap: ${origin}/sitemap.xml\n`);
  writeFileSync(path.join(root, "sitemap.xml"), `<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${origin}/</loc></url><url><loc>${origin}/about/</loc></url></urlset>`);
  return root;
}

function run(root, more = []) {
  const result = spawnSync("python3", [script, "--site", root, "--base-url", origin, "--format", "json", ...more], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("scores a valid built site while showing unmeasured external coverage", () => {
  const root = site();
  try {
    const report = run(root);
    assert.equal(report.pages, 2);
    assert.equal(report.score, 100);
    assert.equal(report.coverage, 53.06);
    assert.equal(report.scoring_version, 2);
    assert.equal(report.score_bounds.lower, 53.06);
    assert.equal(report.complete, false);
    assert.equal(report.checks.find((check) => check.id === "performance.lcp").status, "unmeasured");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("reports broken links and duplicate titles with exact file locations", () => {
  const root = site();
  try {
    const file = path.join(root, "about/index.html");
    const html = `<!doctype html><html lang="en"><head><title>Home | Example</title><meta name="description" content="About us."><meta name="viewport" content="width=device-width"><link rel="canonical" href="${origin}/about/"></head><body><h1>About</h1><a href="/missing/">Read more</a></body></html>`;
    writeFileSync(file, html);
    const report = run(root);
    assert.ok(report.score < 100);
    assert.equal(report.checks.find((check) => check.id === "technical.internal_links").status, "fail");
    assert.equal(report.checks.find((check) => check.id === "onpage.unique_title").status, "fail");
    assert.ok(report.checks.find((check) => check.id === "onpage.link_text").findings.some((item) => item.location === "about/index.html" && item.status === "fail"));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("dated external evidence makes coverage complete", () => {
  const root = site();
  try {
    const common = { source: "reviewed export", date: "2026-01-01", scope: origin, period: "2025-12-01 to 2025-12-28" };
    const checks = {
      "technical.indexing": { ...common, status: "pass", detail: "Search Console indexing and selected canonical reviewed" },
      "technical.http": { ...common, status: "pass", detail: "Live redirects, status and headers reviewed" },
      "onpage.intent_review": { ...common, status: "pass", detail: "Search intent, content quality and cannibalization reviewed" },
      "geo.review": { ...common, status: "pass", detail: "Citations and answer visibility reviewed" },
      "offpage.review": { ...common, status: "pass", detail: "Referring domains and anchor profile reviewed" },
      "performance.lcp": { ...common, kind: "field_p75", value: 2400 },
      "performance.inp": { ...common, kind: "field_p75", value: 180 },
      "performance.cls": { ...common, kind: "field_p75", value: 0.08 },
    };
    const passed = (ids) => Object.fromEntries(ids.map((id) => [id, { status: "pass", detail: "Reviewed fixture criterion with retained supporting evidence" }]));
    checks["onpage.intent_review"].pages = Object.fromEntries(["/", "/about/"].map((route) => [`${origin}${route}`, {
      page_type: "generic", items: passed(["intent", "original_value", "accuracy", "responsibility", "completion", "presentation", "discovery", "metadata"]),
    }]));
    checks["geo.review"].items = passed(["access", "claims", "identity", "measurement"]);
    checks["offpage.review"].items = passed(["link_evidence", "link_quality", "identity"]);
    const file = path.join(root, "evidence.json");
    writeFileSync(file, JSON.stringify({ checks }));
    const report = run(root, ["--evidence", file]);
    assert.equal(report.coverage, 100);
    assert.equal(report.complete, true);
    assert.equal(report.score, 100);
    checks["performance.lcp"].value = 2800;
    writeFileSync(file, JSON.stringify({ checks }));
    const slow = run(root, ["--evidence", file]);
    assert.equal(slow.checks.find((check) => check.id === "performance.lcp").status, "fail");
    assert.equal(slow.score, 96);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("follow-up distinguishes new and resolved failures with comparable coverage", () => {
  const root = site();
  try {
    const initial = run(root);
    const baseline = path.join(root, "baseline.json");
    writeFileSync(baseline, JSON.stringify(initial));
    const file = path.join(root, "about/index.html");
    const original = readFileSync(file, "utf8");
    writeFileSync(file, `<!doctype html><html lang="en"><head><title>About | Example</title><meta name="description" content="About us."><meta name="viewport" content="width=device-width"><link rel="canonical" href="${origin}/about/"></head><body><h1>About</h1><a href="/missing/">Broken destination</a><img src="/logo.png" alt="Example logo"></body></html>`);
    const followup = run(root, ["--baseline", baseline]);
    assert.ok(followup.comparison.score_delta < 0);
    assert.deepEqual(followup.comparison.new_failures, [{ check: "technical.internal_links", location: "about/index.html" }]);
    writeFileSync(baseline, JSON.stringify(followup));
    writeFileSync(file, original);
    const restored = run(root, ["--baseline", baseline]);
    assert.deepEqual(restored.comparison.resolved_failures, [{ check: "technical.internal_links", location: "about/index.html" }]);
    assert.ok(restored.comparison.score_delta > 0);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("follow-up with new evidence does not claim a comparable score change", () => {
  const root = site();
  try {
    const baseline = path.join(root, "baseline.json");
    writeFileSync(baseline, JSON.stringify(run(root)));
    const evidence = path.join(root, "evidence.json");
    writeFileSync(evidence, JSON.stringify({ checks: { "technical.indexing": {
      status: "pass", detail: "Sampled URL Inspection results agree with declared canonicals",
      source: "Search Console export", date: "2026-01-01", period: "2025-12-01 to 2025-12-28", scope: origin,
    } } }));
    const report = run(root, ["--evidence", evidence, "--baseline", baseline]);
    assert.equal(report.coverage, 58.16);
    assert.equal(report.comparison.coverage_delta, 5.1);
    assert.equal(report.comparison.score_delta, null);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("offline audit rejects repository destinations and inputs before overwriting files", (t) => {
  const root = site();
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const repository = path.resolve(path.dirname(script), "../..");
  const output = path.join(repository, "audit-review-test.json");
  assert.equal(existsSync(output), false);
  for (const [label, value] of [["output", output], ["output", repository], ["site", repository], ["evidence", path.join(repository, "package.json")], ["baseline", path.join(repository, "package.json")]]) {
    const result = spawnSync("python3", [script, "--site", root, "--base-url", origin, `--${label}`, value], { encoding: "utf8" });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /must be outside the seo-kit repository/);
  }
  assert.equal(existsSync(output), false);
  const link = path.join(root, "linked-kit");
  symlinkSync(repository, link, process.platform === "win32" ? "junction" : "dir");
  const result = spawnSync("python3", [script, "--site", root, "--base-url", origin, "--output", path.join(link, "audit-review-test.json")], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /must be outside/);
  assert.equal(existsSync(output), false);
});

test("offline audit atomically exports outside the kit and preserves baseline aliases", (t) => {
  const root = site();
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const baseline = path.join(root, "baseline.json");
  const original = JSON.stringify(run(root));
  writeFileSync(baseline, original);
  const alias = path.join(root, "baseline-link.json");
  // A hard link is not used: this checks resolved symbolic aliases.
  if (process.platform !== "win32") symlinkSync(baseline, alias);
  for (const target of process.platform === "win32" ? [baseline] : [baseline, alias]) {
    const result = spawnSync("python3", [script, "--site", root, "--base-url", origin, "--baseline", baseline, "--output", target], { encoding: "utf8" });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /must not overwrite/);
    assert.equal(readFileSync(baseline, "utf8"), original);
  }
  const output = path.join(root, "report.json");
  writeFileSync(output, "Previous report\n");
  const result = spawnSync("python3", [script, "--site", root, "--base-url", origin, "--format", "json", "--output", output], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(readFileSync(output, "utf8")).pages, 2);
});
