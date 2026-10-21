import assert from "node:assert/strict";
import { existsSync, lstatSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { scalar } from "../scripts/lib.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const expectedSkills = [
  "agentic-search-readiness",
  "assets-optimization-checklist",
  "google-data",
  "seo-geo-checklist",
  "seo-mcp-setup",
  "seo-offpage-checklist",
  "seo-onpage-checklist",
  "seo-optimization",
  "seo-pagespeed-optimizer",
  "seo-technical-checklist",
];
const expectedAgents = ["seo-audit.md", "seo-offpage.md", "seo-onpage.md", "seo-optimization.md", "seo-technical.md"];

test("agent descriptions decode quoted punctuation without changing their text", () => {
  const description = 'Audit this project. Triggers: "links", "brand mentions".';
  assert.equal(scalar(`description: ${JSON.stringify(description)}`, "description"), description);
  assert.equal(scalar("name: seo-audit", "name"), "seo-audit");
  assert.equal(scalar("name: seo-audit", "description"), "");
});

function filesRecursively(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const filePath = path.join(directory, entry.name);
    return entry.isDirectory() ? filesRecursively(filePath) : [filePath];
  });
}

test("inventory stays strictly SEO/GEO scoped", () => {
  assert.deepEqual(readdirSync(path.join(root, ".agents", "skills")).sort(), expectedSkills);
  assert.deepEqual(readdirSync(path.join(root, ".agents", "agents")).sort(), expectedAgents);
});

const dataForSeoGuide = ".agents/skills/seo-mcp-setup/DATAFORSEO.md";
const dataForSeoSource = "https://github.com/dataforseo/mcp-server-typescript";
const dataForSeoRevision = "1fc6d197f1141cca8d1a242e15804c5adc41916a";
const dataForSeoIntegrationReferences = new Set([
  "https://mcp.dataforseo.com/v3/mcp",
  dataForSeoSource,
  ...[
    "package.json",
    "src/core/tools/api-request-tool.ts",
    "src/core/tools/tool-annotations.ts",
    "src/core/middleware/api-request/live-endpoint-api-request-middleware.ts",
    "src/core/config/field-configuration.ts",
  ].map((file) => `${dataForSeoSource}/blob/${dataForSeoRevision}/${file}`),
  "https://docs.dataforseo.com/v3/appendix/errors/",
  "https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live/",
  "https://docs.dataforseo.com/v3/backlinks/summary/live/",
]);

function approvedDataForSeoIntegrationReference(file, url) {
  return file === dataForSeoGuide && dataForSeoIntegrationReferences.has(url.href);
}

test("public Markdown references use approved publishers or repository/example targets", () => {
  const files = [path.join(root, "AGENTS.md"), path.join(root, "README.md"),
    ...filesRecursively(path.join(root, "docs")),
    ...["skills", "agents", "runtime", "context"].flatMap((name) => filesRecursively(path.join(root, ".agents", name)))];
  const googleHosts = new Set(["developers.google.com", "support.google.com", "web.dev", "developer.chrome.com", "search.google.com", "status.search.google.com", "www.googleapis.com"]);
  const googleRepositories = new Set(["/googleanalytics/google-analytics-mcp", "/ChromeDevTools/chrome-devtools-mcp"]);
  for (const file of files.filter((name) => name.endsWith(".md"))) {
    const source = readFileSync(file, "utf8");
    for (const match of source.matchAll(/https?:\/\/[^\s<>"'`\\)\]}]+/g)) {
      const url = new URL(match[0]);
      const example = /^(?:[a-z0-9-]+\.)*(?:example\.(?:org|com|net)|example|test|invalid)$/.test(url.hostname);
      const repository = url.hostname === "github.com" && ["/raulveneri/seo-kit", "/raulveneri/seo-kit.git"].includes(url.pathname);
      const google = googleHosts.has(url.hostname) || (url.hostname === "github.com" && googleRepositories.has(url.pathname));
      const integration = approvedDataForSeoIntegrationReference(path.relative(root, file).split(path.sep).join("/"), url);
      assert.ok(example || repository || google || integration, `${path.relative(root, file)} contains an unapproved reference host`);
    }
  }
});

test("DataForSEO reference exception stays limited to the integration guide and exact reviewed URLs", () => {
  const endpoint = new URL("https://mcp.dataforseo.com/v3/mcp");
  assert.equal(approvedDataForSeoIntegrationReference(dataForSeoGuide, endpoint), true);
  assert.equal(approvedDataForSeoIntegrationReference("docs/SCORING.md", endpoint), false);
  assert.equal(approvedDataForSeoIntegrationReference(dataForSeoGuide, new URL("https://mcp.dataforseo.com/other")), false);
  assert.equal(approvedDataForSeoIntegrationReference(dataForSeoGuide, new URL(`${dataForSeoSource}/blob/master/package.json`)), false);
  assert.equal(approvedDataForSeoIntegrationReference(dataForSeoGuide, new URL("https://mcp.dataforseo.com.example.org/v3/mcp")), false);
});

test("all three adapter formats exist for every agent", () => {
  for (const agentFile of expectedAgents) {
    const name = path.basename(agentFile, ".md");
    assert.ok(existsSync(path.join(root, ".agents", "adapters", "claude", "agents", `${name}.md`)));
    assert.ok(existsSync(path.join(root, ".agents", "adapters", "codex", "agents", `${name}.toml`)));
    assert.ok(existsSync(path.join(root, ".agents", "adapters", "opencode", "agent", `${name}.md`)));
    const claude = readFileSync(path.join(root, ".agents/adapters/claude/agents", `${name}.md`), "utf8");
    assert.ok(claude.startsWith("---\n"), "Claude agents must begin with YAML frontmatter");
    assert.doesNotMatch(claude, /^model:/m, "inherit the user's configured model instead of pinning a provider/model");
    const codex = readFileSync(path.join(root, ".agents/adapters/codex/agents", `${name}.toml`), "utf8");
    assert.doesNotMatch(codex, /^model\s*=/m);
  }
});


test("resources and executable tooling live under .agents without root aliases", () => {
  for (const name of ["skills", "agents", "runtime", "adapters", "scripts", "tests", "install"]) {
    assert.ok(lstatSync(path.join(root, ".agents", name)).isDirectory());
    assert.throws(() => lstatSync(path.join(root, name)), { code: "ENOENT" });
  }
});
