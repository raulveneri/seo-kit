# Audit CLI capabilities

`last_reviewed: 2026-10-21` | SQLite schema 3 | Live report schema 2 | Rules version 2

Check this table before interpreting an audit result. It shows what the tools measure and what still needs review. Automated findings alone cannot establish SEO quality, rich-result eligibility or WCAG conformance.

**Implemented** means the feature has usable output and tests. **Tested adapter** means controlled responses exercise its contracts, limits and failures. Live account verification still requires access to that account. Missing, blocked or over-budget evidence stays **unmeasured**.

| Area | Status | Output and verification scope |
| --- | --- | --- |
| Persistent crawling | Implemented | SQLite queue, writer lock and recovery of processing URLs. Budget, time, disk and SIGTERM tests. URL limits 100/500/unlimited. |
| Local privacy and retention | Implemented with bounded filters | CLI HTML retention none/raw/rendered/both, credential filtering on new writes and exclusions for sensitive URL parameters. Metadata-only resume re-fetches bodies. Allowlisted sharing export, retention preview/apply and protected runs. Existing data is not scrubbed, not encryption or general anonymization. |
| Robots and sitemaps | Implemented | Agent groups, specificity, Allow on ties, wildcards, end anchors and reserved escapes. Nested indexes, bounded gzip expansion, provenance, errors and `--max-sitemaps`. |
| Parameters and exclusions | Implemented | Explicit normalization, stable repeated-value ordering, path/parameter exclusions and exclusion queue. |
| Responses and redirects | Implemented | Status, repeated headers, HTTP chains and errors. Refresh and JavaScript candidates with evidence. External status checks respect resource/robots budgets. Unexecuted JavaScript candidates remain unconfirmed. |
| Indexability and canonicals | Implemented | HTML/HTTP canonical conflicts, combined meta robots and X-Robots-Tag, noindex/nofollow, sitemap exclusions and optional URL Inspection. |
| Metadata and headings | Implemented | Multiple or missing titles/descriptions, duplicates, H1/H2 and skipped levels. Configurable thresholds are labeled heuristics. |
| Links and architecture | Implemented | Anchors, `rel`, internal/external targets and PDF links. BFS depth, incoming/outgoing links and orphans within the sample. CSV/JSON graph. |
| Images | Implemented | Inventory, alt, bytes, format and raster dimensions or SVG attributes. Authorized hosts, errors, budgets and image sitemaps. |
| Hreflang and pagination | Implemented | Language registry validation, self-reference, reciprocity and authorized external alternates. Next/prev return links. Unfetched targets stay unmeasured. |
| Duplicates | Implemented | Exact SHA-256, duplicate metadata and language-separated SimHash main-content candidates. Bounded comparisons and template-match tests. Editorial decisions remain human. |
| Structured data | Implemented with declared profiles | JSON-LD syntax, typed nodes, profile properties for Article/Product/Organization and visible-content mismatches. Records profile and review needs. Does not establish Google eligibility. |
| PDF and AMP | Implemented | PDF metadata, text and links with a 100-page cap and time/memory-bounded subprocess. Official local AMP WASM validator and SHA-256. Valid/invalid fixtures. Encrypted, image-only or failed PDFs need external review/OCR. |
| Accessibility | Automated checks implemented | Static checks and axe-core in Chromium. Violations, selectors, executed rules and incomplete results. Manual review stays separate and unmeasured. |
| Spelling and grammar | Implemented | Project dictionary, language, frequency and SHA-256. Explicitly authorized HTTPS LanguageTool, engine version, matches, truncation and failures. Human suggestion review. |
| Custom extraction | Implemented | Named CSS/XPath fields, attributes/text/scalars, received HTML/DOM, result limits, selector errors and JSON/CSV export. |
| Rendering | Implemented with real Chromium tests | Headless Shell, inherited seccomp or namespace isolation, resources served through the safe client, blocked writes/WebSockets/WebRTC. HTML/DOM differences, failed scripts and blocked resources. Public/private direct-connection rejection tests. |
| Sitemap and graph exports | Implemented | Image sitemap, noindex/canonical handling, URL/byte-bounded parts and index. Streamed CSV/JSON graph. |
| GA4 and GSC performance | Tested adapters | Budgeted pagination, property/period/date, normalized URL reconciliation, scoped cache, missing credentials and invalid responses. GSC does not guarantee every row. |
| URL Inspection | Tested adapter | Priorities, per-run quota, reuse, retries and immediate persistence of partial successes. Scores only with complete coverage and usable verdicts. |
| PageSpeed Insights | Tested adapter | Lighthouse lab audits, categories, environment, errors and warnings. No usable score means unmeasured. |
| CrUX | Tested adapter | Mobile field records by origin and URL, collection period and explicit absence. Separate from lab data. |
| Moz and backlink CSV | Tested adapter | JSON-RPC and normalized CSV. 50-row maximum, database-local monthly reservations, sample coverage and errors. Does not track other tools/databases or represent a full link index. |
| Queries and exports | Implemented | Compatible filters, SQL pagination, indexes, streamed export and atomic writes. 20,000-row no-loss test. No million-row benchmark claim. |
| Comparisons and migrations | Implemented | Added/removed URLs, responses, content, metadata, links, structure and issues. Streaming without bodies, URL maps, collision rejection and scope differences. 2,000 changed-URL test. |
| Scheduling | Implemented | External job files, one-off/periodic runs, dated reports, JSONL status and subprocess timeout. |

## Optimization workflow

Use the `seo-optimization` agent and skill to find opportunities, compare proposals, implement authorized work and check the result. If several strategies make sense, the user chooses. With one reasonable path, the assistant explains why and continues. The CLI supplies audit evidence for this work. Recommendations need the website's own context and data, and search outcomes need later measurement. For a new site, planning can start with declared requirements and explicit assumptions.

## Verification limits

The workflows cover current Google generative impression reporting and effective inclusion settings. These require an authorized export or read-only account evidence. The CLI's Search Analytics adapter does not collect them. No new API integration or scoring criterion is implied. See the [optimization evidence reference](../.agents/skills/seo-optimization/KNOWLEDGE.md) for checked Google sources and dates.

API suites use controlled responses, not live credentials. Check permissions, purchased quotas, real data and correspondence with GA4/GSC/Moz reports in the project that declares those accounts. Grammar tests exercise the LanguageTool contract. The kit supplies neither a server nor the project's dictionary. Missing access is never marked passed.

Disk checks happen between transactions. A strict physical limit needs a filesystem quota. Crawls retain operational budgets even without a URL cap. Summary scoring uses version 2 with the existing category budgets and revised evidence/applicability accounting. It exposes category/page assessments and checklist bounds. See [SCORING.md](SCORING.md). Inspect advanced findings in `issues` and `observations` rather than inventing new SEO weights.

The [MCP setup skill](../.agents/skills/seo-mcp-setup/SKILL.md) is a connection guide, not a bundled connector or a live-account test. [PageSpeed optimization](../.agents/skills/seo-pagespeed-optimizer/SKILL.md) is an implementation workflow in an authorized consuming project. It does not turn a CLI score into accessibility certification.

Google Business Profile setup covers account/location discovery, profile information, reviews and daily performance through a selected MCP bridge or authorized API/export binding. Each capability needs its own access check. The kit bundles no Business Profile MCP server or CLI adapter. See the [provider procedure and Google reference ledger](../.agents/skills/seo-mcp-setup/KNOWLEDGE.md#google-business-profile), checked 2026-10-21.

DataForSEO has a [provider-specific MCP guide](../.agents/skills/seo-mcp-setup/DATAFORSEO.md), checked 2026-10-21, for remote/local registration, authentication, keyword/SERP/backlink capability checks and controlled spending. This is documented external MCP support, not a bundled server, audit CLI adapter or live-account verification. Provider integration references are kept in that guide.

## Google technical references

Checked 2026-10-20:

- [GA4 reporting and pagination](https://developers.google.com/analytics/devguides/reporting/data/v1/basics).
- [Search Analytics](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
- [PageSpeed Insights](https://developers.google.com/speed/docs/insights/rest/v5/pagespeedapi/runpagespeed).
- [CrUX](https://developer.chrome.com/docs/crux/api).

## Changelog

- 2026-10-21: Added DataForSEO MCP connection guidance, workflow routing, full-field export handling and budget/error verification. No paid request or live account test was run.

- 2026-10-21: Added Google Business Profile connection guidance and first-party evidence routing. No bundled connector, CLI adapter or live account verification is implied.

- 2026-10-21: Added scoring version 2, per-page content evidence, conditional content tasks, partial/N-A accounting and comparison compatibility guards. Corrected automatic length and self-canonical penalties.

- 2026-10-21: Updated manual workflows for current Google AI controls and impression reporting, retired rich results and dated rollout checks. CLI schemas, automated coverage and scoring remain unchanged.
- 2026-10-20: Added local crawl privacy controls, configurable HTML retention, reduced sharing exports, protected crawls and optional retention. Metadata-only resume re-fetches HTML. Extraction reports unavailable retained source explicitly. Added privacy integration and CLI tests. The filters do not provide general anonymization.
- 2026-10-19: Added the SEO optimization agent workflow for critically compared proposals, one or more recommendations, user choice where needed, authorized implementation and follow-up. CLI scoring and search rules are unchanged.

- 2026-10-19: Documented skill boundaries and the validation scope for implemented checks.
- 2026-10-19: SQLite 3, observations and rules 2. Advanced engines, volume tests, pinned dependencies and isolated Chromium. Automated checks retain the documented coverage limits.
- 2026-10-19: Initial persistence, adapter, rule and export matrix.
