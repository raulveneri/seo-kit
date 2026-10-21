# Use SEO Kit

Choose one site and define what you want to check. Keep its reports, credentials and databases in the project's approved locations. Read that project's context before using the kit's tools.

For installation, assistant discovery and a first scoped proposal, follow the [first task guide](GETTING_STARTED.md). The [README task selector](../README.md#choose-the-first-task) provides requests for optimization, new-site planning, audits, comparisons and data connections.

## One project folder per website or client

Use a dedicated folder for each website or client. Open that folder as the active project in your assistant before requesting work. You can reuse a website's source folder or create an SEO working folder without code or Git.

For example, keep client projects alongside the kit in separate folders:

```text
workspace/
  seo-kit/
  clients/
    client-a-website/
      keyword-research/
      audits/
      proposals/
      reports/
    client-b-website/
      audits/
      proposals/
```

Select `client-a-website/` to work on that website. Select `client-b-website/` when switching to the other one. For a client with several websites, give each website its own project folder. Names and parent folders are up to you. The assistant creates only the output folders needed for the task inside the selected project.

This keeps each website's context, research and results together when you work with several clients. Reuse the same project folder for later tasks to preserve its history. If several folders are open, identify the target before the assistant writes files. Running a CLI command from `seo-kit/` still requires absolute input and output paths for the selected client project.

## Generated files in the selected project

The selected project is the client or website folder open in the assistant. It can be an SEO working folder without a website codebase or Git repository. The assistant resolves that folder before writing, even when it runs kit commands from a different directory. If several projects are open and the target is unclear, it asks which one to use.

| Output | Folder created inside the selected project |
| --- | --- |
| Keyword research, query exports, clusters and keyword-to-page maps | `keyword-research/` |
| Audits, crawl databases, evidence, performance/accessibility measurements and comparisons | `audits/` |
| Proposals grouped by type, selected plans and implementation tracking | `proposals/<type>/` |
| Standalone performance, AI-visibility and progress reports | `reports/DD/MM/YYYY/` |

Directories are created when first needed. Proposals are grouped by type: `proposals/articles/`, `proposals/guides/`, `proposals/landings/`, `proposals/technical/` or `proposals/strategy/`. Create another descriptive type when needed. Each proposal keeps its evidence, decision and implementation tracking together in a dated topic directory. Related proposals link to one another.

Standalone reports use nested day/month/year directories, such as `reports/19/10/2026/search-performance/`. Use zero-padded day and month and the project's timezone, or UTC if none is declared. This is the report creation date. The measured period is recorded inside the report. Repeated reports use a distinct time or run suffix. Audit reports and supporting exports stay with the audit in `audits/`.

Other deliverable types use a descriptive kebab-case folder in the same project. Preserve earlier results and do not relocate existing client files without a migration request. The assistant saves substantive deliverables and returns their paths with its summary. Technical and off-page agents can save reports while keeping website source and configuration read-only. Resolved destinations must remain inside the selected project and outside the kit checkout, including when symlinks are present. Deliverables stay outside published asset and build directories. Credentials and tokens do not belong in reports.

### Keyword research records

Keyword research includes **keyword, monthly volume, search intent, paid competition and CPC**, followed by organic difficulty, source, market, language, engine, device, network, currency, dates and measurement periods. Missing values remain explicit. Paid competition and organic difficulty are separate metrics.

Collect all available business fields from an authorized connected tool within the authorized scope and budget. Preserve monthly histories, bids, trends, related terms, SERP results/features and any further returned fields. Keep provider-specific data and incompatible scopes separate. Added fields extend the same stable column groups instead of replacing the core or discarding earlier data.

Each `keyword-research/YYYY-MM-DD-topic/` run contains a readable research summary, complete CSV and typed JSON records, a metadata/coverage manifest and sanitized raw responses. Available monthly histories, SERP items and other nested data are retained in linked sidecars. The [keyword research contract](../.agents/skills/seo-optimization/KEYWORD_RESEARCH.md) defines field order, sorting, missing values, provider extensions and delivery checks.

Example layout inside the selected client folder:

```text
keyword-research/
  2026-10-19-services/
    research.md
    keywords.csv
    keywords.json
    manifest.json
    raw/
proposals/
  articles/
    2026-10-19-topic/
      proposal.md
  guides/
  landings/
audits/
  2026-10-19-baseline/
reports/
  19/
    10/
      2026/
        search-performance/
```

Only directories needed for the current task are created. The tree illustrates possible destinations.

When running the CLI manually, create the destination first and pass absolute paths. The CLI cannot infer which client folder is selected in an assistant, so the examples use `/path/to/project` as a placeholder for that folder. For separate audit runs, use distinct dated paths or subdirectories rather than reusing the example filenames.

## Optimize a website

Use the `seo-optimization` agent and [skill](../.agents/skills/seo-optimization/SKILL.md) to decide what to improve and carry the work through to verification. Start with the website's goals and constraints. Compare useful proposals with their evidence, assumptions, effort and risks. If several strategies make sense, you choose before the work that depends on that choice. With one reasonable path, the assistant explains it and continues within your authorization.

An audit can supply the baseline, but a new website can start from its requirements and current implementation. Historical analytics is useful evidence when available, not a prerequisite for a provisional plan. A proposal-only request produces alternatives and a recommendation without applying changes. Routine decisions within an authorized implementation task do not require repeated approval.

## Installation and synchronization

Global setup supports Windows, macOS and Linux, with a cron fallback for additional Unix systems. Git, GitHub CLI (`gh`) and Node.js 22 or newer are required for installation. The optional audit tools require their own Python runtime.

```bash
npm run setup:dry-run
npm run setup
npm run doctor
npm run setup:status
```

Setup installs an owner-approved release into the [managed user data directory](INSTALLATION.md#data-and-discovery-paths), outside the active project. On Windows this is `%USERPROFILE%\.local\share\ai-kits\seo-kit`, independent of LocalAppData virtualization in Codex Desktop. It copies individual kit resources into native assistant discovery paths and merges a marked routing block into global instructions. It preserves other resources and refuses conflicting or locally edited files. A setup dry-run performs no writes or Git/network operations.

Automatic updates run in the background at login/startup and daily at 00:00 in the computer's local time zone through Windows Task Scheduler, macOS launchd, a Linux user systemd timer or cron. Offline failures retry on the next scheduled run. Updates stage and validate a new commit before activating it, retain the previous release and recover interrupted integration writes on the next invocation. Local changes, origin changes or divergent history stop activation. Only published upstream repository changes are downloaded. No knowledge research jobs run automatically.

```bash
npm run sync
npm run setup:rollback
npm run setup:remove
```

Use `npm run setup -- --no-services` to explicitly opt out of automatic updates. Scheduler registration failure makes setup fail with a diagnostic even when resource installation succeeded. [Installation details](INSTALLATION.md) document stable launchers, logs, migration, discovery checks and platform limitations.

## Repository validation

The [GitHub Actions workflow](../.github/workflows/validate.yml) runs `npm run validate` on Ubuntu with Node.js 22 and Python 3.12, plus isolated global-installation tests on Windows, macOS and Ubuntu for pushes to `main` and pull requests targeting `main`. It can also be started manually in the Actions tab after the workflow is on the default branch. Node dependencies use `npm ci`. Python dependencies use the hash-locked audit manifest. A final check rejects modified, deleted or newly generated adapters absent from the commit.

The job has read-only repository permissions and requires no website credentials. It does not install user-level links, enable synchronization, crawl public websites or publish changes. The suite uses controlled API responses. It does not verify real accounts. Browser integration tests remain opt-in, and the official AMP test skips when its separately downloaded validator is absent. Use `npm run setup:audit` and `npm run test:browser` in a supported environment for those engines.

The result appears as `Repository validation` in GitHub. A failed result reports a problem but does not itself prohibit merging. Enforcing a required check needs a separately configured repository rule. Local validation remains `npm run validate`.

Validation includes `npm run check:private-data`. This scans tracked files and non-ignored new files for selected credential formats, environment files, non-example email addresses and personal home paths. Known synthetic home paths are allowed only in tests. Example email domains and GitHub noreply addresses are allowed. Findings report a file, line and category without printing the matching value. This is a bounded worktree check: it does not inspect Git history, classify arbitrary personal notes or detect every secret format. Keep the existing project-identity checks too.

## Crawl a public website

```bash
mkdir -p /path/to/project/audits
npm install
npm run setup:audit
npm run audit:live -- --url https://example.org/ --crawl-limit 100 --database /path/to/project/audits/crawl.sqlite --format json --output /path/to/project/audits/audit-live.json
```

`setup:audit` prepares the pinned Python dependencies from `.agents/requirements-audit.lock`, Playwright Chromium and the official AMP WASM validator under `~/.local/share/seo-kit/`. The launcher selects the managed runtime. `SEO_KIT_PYTHON` can select a project-managed interpreter.

The crawler accepts public HTTPS on port 443, checks robots and restricts navigation and redirects to the same origin. It blocks private and reserved addresses after DNS resolution. URLs come from the start page, internal links and sitemaps.

Choose `--crawl-limit 100|500|unlimited`. The default is 100 responded URLs, including errors. `unlimited` removes only that cap: request, time, response-size, storage and rate limits still apply. Use `--max-requests` (default 2000), `--max-seconds`, `--max-disk-bytes`, `--max-response-bytes` and `--delay` to set them. Disk checks run between transactions. Enforce a filesystem quota if a strict physical limit is required.

`--exclude-parameter` and `--exclude-path` add explicit exclusions. Parameter sorting preserves repeated-value order. `--resume` continues an interrupted crawl with matching settings. Changed robots or sitemap URLs require a new crawl. Only one writer can use a database at a time. If only `--output` is provided, the database is created beside it with a `.sqlite` extension.

### Rendering and specialist engines

`--render auto` tries Chromium for JavaScript-dependent pages. `always` requires rendering. `never` uses received HTML. Rendering requires Linux, Playwright 1.48 or newer and supported isolation. The preferred Chromium Headless Shell uses an inherited libseccomp allowlist. A user/network namespace is the fallback. Without isolation, `auto` retains HTML and warns, while `always` fails. The kit does not change global AppArmor settings. `SEO_KIT_CHROMIUM_PATH` selects a compatible browser executable.

The parent process serves authorized requests through the bounded HTTPS client. `--resource-host` permits named external image, alternate or rendering hosts, with robots and redirect checks. Browser navigation stays on the audited origin. Writes, WebSockets, WebRTC and WebTransport are blocked. `npm run test:browser` tests the real browser, direct connection blocking and HTML/DOM storage.

`--resource-limit` bounds image and external-target analysis. Images include bytes, format and dimensions. PDF extraction has time/memory limits and a 100-page cap. Encrypted or unextractable files remain unmeasured. `--amp-validator <local-bundle>` uses the official validator without downloading it during the crawl and records its SHA-256. axe-core records violations, incomplete checks and executed rules. Manual accessibility review is still required.

`--max-sitemaps` bounds sitemap documents, including nested indexes and expanded gzip. Observation thresholds are configurable heuristics, not Google limits:

```bash
npm run audit:live -- --url https://example.org/ --thresholds '{"title_max":60,"description_max":160,"image_max_bytes":200000}' --format json
```

## Data connections

Use [seo-mcp-setup](../.agents/skills/seo-mcp-setup/SKILL.md) for MCP registration and verification. The following CLI adapters call APIs directly. They do not install MCP servers.

For DataForSEO, follow the [complete MCP connection guide](../.agents/skills/seo-mcp-setup/DATAFORSEO.md). It covers remote OAuth, pinned local stdio, Claude Code/Codex/OpenCode registration, capability checks, full keyword exports, budgets and errors. Connect it in the consuming project's assistant profile. Kit installation does not register it, and the audit CLI has no DataForSEO adapter.

For Google Business Profile (formerly Google My Business), use the [provider setup procedure](../.agents/skills/seo-mcp-setup/KNOWLEDGE.md#google-business-profile) to select a bridge and verify profile, reviews and performance access separately. The kit does not include a Business Profile MCP server or CLI adapter. An authorized export can supply evidence when no bridge is selected.

| Data | Flags | Project environment |
| --- | --- | --- |
| GA4 | `--ga4-property <id> --period-start <date> --period-end <date>` | `SEO_KIT_GA4_ACCESS_TOKEN` |
| GSC performance | `--gsc-property <property> --gsc-performance --period-start <date> --period-end <date>` | `SEO_KIT_GSC_ACCESS_TOKEN` |
| URL Inspection | `--gsc-property <property> --max-inspections <n>` | `SEO_KIT_GSC_ACCESS_TOKEN` |
| PSI lab results | `--psi-limit <n>` | `SEO_KIT_PSI_API_KEY` |
| CrUX origin and URL field data | `--crux --crux-limit <n>` | `SEO_KIT_CRUX_API_KEY` |
| Moz backlink sample | `--moz-limit <n>` | `SEO_KIT_MOZ_TOKEN` |

Store secrets outside the kit. `--api-limit` caps rows and URLs. Repeat `--priority-url` for ordered priorities. GA4 and GSC paginate to the budget, and transient HTTP failures allow up to two further retries. URL Inspection defaults to ten URLs and scores indexing only when usable results cover all crawled pages. It describes Google's indexed version, not a live test.

CrUX keeps device, origin/URL and collection period. Missing field records stay unmeasured. PSI keeps Lighthouse diagnostics, environment and warnings separately. Moz reserves at most 50 rows per month in the local database, including failed attempts. This does not track use by other tools or databases and does not represent a complete backlink profile. `external_data` stores source, property, period and fetch date. Completed calls are reused within the same crawl when scope matches.

For an authorized backlink export, use CSV columns `source_url,target_url,anchor_text` and `--backlinks-export <file> --backlinks-source <provider-export> --backlinks-period <period>`. The summary covers up to 10,000 rows. Counts do not automatically pass the off-page quality review.

## Query, extract and compare

For a complete before/after sequence and migration example, use [Check SEO changes before and after](FOLLOW_UP.md). Preserve separate snapshots and inspect scope comparability before interpreting differences.

```bash
mkdir -p /path/to/project/audits
npm run audit:query -- query --database /path/to/project/audits/crawl.sqlite --table issues --severity warning --format csv --output /path/to/project/audits/issues.csv
npm run audit:query -- query --database /path/to/project/audits/crawl.sqlite --table pages --directory https://example.org/blog --format json
npm run audit:query -- query --database /path/to/project/audits/crawl.sqlite --table observations --type architecture --limit 100 --offset 0
npm run audit:query -- compare --before /path/to/project/audits/old.sqlite --after /path/to/project/audits/new.sqlite --format json
npm run audit:query -- sitemap --database /path/to/project/audits/crawl.sqlite --output /path/to/project/sitemap.xml
npm run audit:query -- graph --database /path/to/project/audits/crawl.sqlite --output /path/to/project/audits/links.csv
npm run audit:query -- extract --database /path/to/project/audits/crawl.sqlite --fields /path/to/project/audits/fields.json --format json
```

A fields file can contain `[{"name":"headings","css":"main h2"},{"name":"images","xpath":"//img/@src"}]`. Each field uses CSS or XPath with an optional attribute. `--source` selects received HTML or DOM and `--max-results` limits extraction.

SQLite schema 3 migrates schemas 1 and 2 when the crawler opens them. Queries open the primary database read-only. Comparisons can use temporary mapping tables. `--limit` and `--offset` paginate results, and incompatible filters fail explicitly. Exports replace their destination only after completion. JSON preserves original text. CSV prefixes potentially executable spreadsheet cells with a quote.

`compare` streams page changes without loading HTML bodies. For migrations, pass `--url-map <json-file>` mapping old URLs to new ones. Check `scope_comparable`: different budgets, incomplete crawls or missing cross-origin maps can make apparent additions/removals reflect scope. Live JSON uses schema 2. Older schema 1 reports remain accepted as a summary `--baseline`, but score deltas require matching scoring versions and measured/applicable item sets.

Directory sitemap exports use `--output-directory`, `--public-base` and `--max-urls`, and include images, parts and an index.

`spellcheck --dictionary <utf8-file> --language en` uses a project dictionary with one word per line and returns candidates with frequency and URLs. Unsupported languages remain unmeasured. Suggestions require human review. `grammar --endpoint <authorized-HTTPS-LanguageTool/v2/check> --language <language>` sends page text to the declared service and records engine version, matches and coverage. Bound it with `--max-pages`.

## Schedule a crawl

Save the job as `audits/job.json` inside the selected project. Relative paths resolve from that file. Create `audits/` before saving the job or starting the scheduler.

```json
{
  "url": "https://example.org/",
  "database": "crawl.sqlite",
  "output_directory": ".",
  "crawl_limit": "100",
  "render": "never",
  "max_requests": 2000,
  "max_seconds": 3600,
  "job_timeout_seconds": 3720
}
```

```bash
mkdir -p /path/to/project/audits
npm run audit:schedule -- --job /path/to/project/audits/job.json --once
npm run audit:schedule -- --job /path/to/project/audits/job.json --every-seconds 86400
```

`--once` supports an external scheduler. Periodic mode accepts `--runs <n>`. Each run creates a dated report and emits JSONL with exit status, path and error. Exit status is 1 if any run fails and 130 on interruption. The job timeout stops the subprocess and leaves the database available to resume. Credentials come from the environment. Add `"resume": true` to continue an interrupted crawl. Periodic jobs otherwise create fresh crawls. This schedules site audits, not toolkit maintenance.

## Local crawl privacy, sharing and retention

Crawls remain in SQLite under the selected client's `audits/` directory. The CLI defaults to `--store-html none`: it keeps metadata, findings, links and content fingerprints, while HTML is analysed in private temporary directories and is not retained in SQLite. Choose `--store-html raw`, `rendered` or `both` to retain filtered source for debugging or later extraction. These modes do not anonymize page text. The Python `CrawlStore` and direct `run_live` API keep their legacy `both` default when no policy is passed. Callers should pass the desired mode explicitly.

Without retained HTML, later extraction, spelling and grammar commands report that source is unavailable rather than silently returning no findings. Resume re-fetches completed HTML pages whose bodies were not retained, using the normal robots, request, time and storage limits. Re-fetching observes the site at the new request time. Comparisons still use fingerprints and metadata. Differing privacy settings are reported as a scope/configuration difference.

New writes filter known credential fields (including cookies, authorization, tokens, passwords, API keys and selected signed-URL parameters), recognized credential formats and named password/hidden fields. URLs with sensitive query parameters are excluded from the crawl queue and resource checks. Query parameters such as category and pagination remain. An excluded URL reduces scope completeness. New database files use owner-only permissions on POSIX. This is not encryption, general PII detection or a guarantee that arbitrary credentials cannot occur in content. Existing database rows, exports and backups are not scrubbed automatically.

Use a reduced export for sharing:

```bash
npm run audit:query -- share --database /path/to/client/audits/crawl.sqlite --crawl-id 1 --output /path/to/client/audits/share.json
```

This includes page URLs, status, content type, depth and rule/severity/state summaries. It removes query strings, fragments and email-shaped path values, and omits HTML, metadata text, headers, finding evidence and provider payloads. URLs may still identify clients or people through other path segments. Review them before sharing. Full query/export commands remain available for authorized local analysis and are not anonymous exports. Reading local data into a cloud AI assistant can disclose it to that model's provider. Local storage alone does not constrain the assistant or authorize external API use.

Retention is off by default. List crawls, protect important results, preview a duration and then apply it:

```bash
npm run audit:query -- crawls --database /path/to/client/audits/crawl.sqlite
npm run audit:query -- lock --database /path/to/client/audits/crawl.sqlite --crawl-id 1
npm run audit:query -- retention --database /path/to/client/audits/crawl.sqlite --days 30
npm run audit:query -- retention --database /path/to/client/audits/crawl.sqlite --days 30 --apply
```

`unlock --database <db> --crawl-id <id>` removes protection. Retention deletes only completed, unprotected crawls older than the duration, and their dependent rows. Interrupted/running crawls and shared API quota accounting are preserved. Mutations use the same database writer lock as live audits. `secure_delete` and a WAL checkpoint reduce SQLite remnants. This is not guaranteed erasure from the filesystem, SSD or backups. Retention does not delete report/export files.

To automate retention on future live runs, explicitly set `--retention-days 30`, or `"retention_days": 30` in a scheduled job. Scheduled jobs also accept `"store_html": "both"` (or another storage mode). No existing client database is modified simply by updating this toolkit.

## Audit compiled HTML and supply evidence

```bash
mkdir -p /path/to/project/audits
npm run audit -- --site /path/to/project/dist --base-url https://example.org --format json --output /path/to/project/audits/audit.json
```

This mode makes no network requests. Supply HTML, robots and sitemaps as they would be published. The summary weights are technical SEO 35, on-page 35, GEO 10, Core Web Vitals 10 and off-page 10. Scoring version 2 accounts for measured, missing and non-applicable evidence, gives each page equal influence within a criterion and reports category/page assessments and checklist score bounds. Missing evidence never becomes a pass. Coverage depends on applicability and the measured item set. There is no universal build-only coverage percentage. Read [SCORING.md](SCORING.md) for the formula, migration and interpretation limits.

The offline CLI resolves input and output paths, including symbolic links, and rejects paths inside the kit checkout. Its output must not overwrite the evidence or baseline. File reports use atomic replacement, so a failed write preserves an earlier report.

Use `--evidence <file>` for reviewed external evidence and `--baseline <previous-report>` for a follow-up. Each check needs `source`, ISO `date`, `period` and same-origin `scope`:

```json
{
  "checks": {
    "geo.review": {
      "items": {
        "access": {"status": "unmeasured", "detail": "Effective Search Console inclusion evidence is not yet available."},
        "claims": {"status": "pass", "detail": "Visible claims and the supplied structured data were checked against retained evidence."},
        "identity": {"status": "pass", "detail": "The reviewed page matches the declared business identity."},
        "measurement": {"status": "unmeasured", "detail": "No authorized impression export or repeatable answer sample is available."}
      },
      "source": "project review report",
      "date": "2026-10-14",
      "period": "2026-09-01 to 2026-09-28",
      "scope": "https://example.org"
    },
    "performance.lcp": {
      "kind": "field_p75",
      "value": 2400,
      "source": "CrUX",
      "date": "2026-10-14",
      "period": "2026-09-01 to 2026-09-28",
      "scope": "https://example.org"
    }
  }
}
```

Other review IDs are `technical.indexing`, `technical.http`, `onpage.intent_review` and `offpage.review`. Technical indexing and HTTP require `status: pass|fail` and `detail`. Content review uses per-URL `pages`, `page_type` and `items` from [CONTENT_REVIEW.md](../.agents/skills/seo-onpage-checklist/CONTENT_REVIEW.md). GEO and off-page use the item IDs in [SCORING.md](SCORING.md). Legacy blanket qualitative verdicts remain readable but earn no item-level review credit. `performance.inp` and `performance.cls` require field p75 values, like LCP. NEVER: substitute lab data. Explicit evidence overrides automatic results and needs a traceable justification.

100% coverage means evidence exists for all weighted criteria. It does not establish that every SEO factor was measured or that a supplied human review was correct. JSON-LD validation does not prove rich-result eligibility. Use the [Rich Results Test](https://search.google.com/test/rich-results) and check the visible content. Read [AUDIT_WORKFLOW.md](AUDIT_WORKFLOW.md) for prioritization and repeat measurements, and [CAPABILITIES.md](CAPABILITIES.md) for limits.
