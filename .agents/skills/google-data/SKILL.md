---
name: google-data
description: Read and cite a project's first-party Google Business Profile, Search Console, GA4 and PageSpeed data through bindings declared by that project. Read-only and implementation-agnostic. Use whenever SEO work needs local business performance, search performance, analytics, indexing or Core Web Vitals evidence.
allowed-tools: Bash, Read, Grep, Glob
---

# Read and cite first-party Google data

Choose the source for the question, query it and cite the result. Get property IDs, credential paths and website scripts from the project's own context. NEVER: invent a figure.

## Discover the binding

Read the current project's `AGENTS.md` and its declared analytics/tooling contract.

- If the project declares MCP, API, CLI or authorized-export bindings for Google Business Profile, GSC, GA4 or PageSpeed, use exactly those read-only bindings. Verify which capabilities the binding actually supports.
- If it declares analytics unavailable, or declares nothing, mark the affected items `[not measurable]` and continue without figures.
- NEVER: borrow another project's command, property or credentials.

## Choose the correct source

| Question | Source |
|---|---|
| Queries/pages already receiving impressions, clicks, CTR and average position | Google Search Console performance |
| Impressions in Google AI Overviews and AI Mode | Search Console Generative AI performance report or an authorized export. Verify actual binding coverage |
| Effective inclusion in Search generative AI features | Read-only Search Console settings evidence, including parent-property inheritance, not established by a crawl |
| Indexing status, declared vs Google-selected canonical and sitemap state | Search Console URL Inspection / Sitemaps |
| Sessions, landing pages, channels and events | GA4 |
| Business profile identity and reviews for an authorized location | Business Information and Google My Business review APIs through a declared binding or authorized export. Use `seo-offpage-checklist` for local identity review |
| Local profile daily performance, including website clicks and call clicks | Business Profile Performance API through a declared binding or authorized export. Retain location, dates and metric definitions |
| Lab diagnostics and public field data for LCP, INP and CLS | PageSpeed Insights / CrUX |
| Backlinks | An authorized Search Console Links report export or another declared source, not supplied by this kit's performance API adapter |
| Provider authority metrics or keyword volume/difficulty | Request a suitable declared source. These are not Search Console performance metrics |

## Blockers (MUST / NEVER)

- [ ] MUST: every figure includes source, query date, property/site scope and time range.
- [ ] MUST: comparisons declare both periods and use comparable dimensions and filters.
- [ ] NEVER: invent, estimate or visually round a missing metric. Write `no data` or `[not measurable]`.
- [ ] NEVER: expose credentials, tokens, property secrets or raw personal data.
- [ ] NEVER: use one project's analytics binding while working in another repository.
- [ ] NEVER: present PageSpeed lab data as CrUX field data, or vice versa.
- [ ] MUST: for a URL that is not public or has no history, state that limitation instead of forcing a result.

## Keep queries focused (SHOULD)

- [ ] SHOULD: Request only the dimensions and metrics needed.
- [ ] SHOULD: Default to a clearly stated 28-day window unless the analysis calls for another period.
- [ ] SHOULD: Prefer compact table output for review and structured output only when another step consumes it.
- [ ] SHOULD: Account for source latency and state the effective end date returned by the tool.

## Generative report limits

The [Generative AI performance report](https://support.google.com/webmasters/answer/16984139) documents impressions with page, country, date and device dimensions. Preserve reporting timezone, property/page aggregation and export limitations. An absent report is not proof of zero visibility. Do not derive AI clicks, CTR, positions or conversions from these impressions. A bridge exposing Search Analytics does not automatically expose this report. Request an authorized export when needed. The existing CLI adapter does not collect it.

The [Search generative AI control](https://support.google.com/webmasters/answer/16908024) has effective and inherited property choices. Observe them only through authorized evidence and keep account changes outside this read-only workflow. These references were checked 2026-10-21. Google notes worldwide availability from 2026-08-31.

## Failure handling

For Business Profile, follow the [connection procedure and checked Google references](../seo-mcp-setup/KNOWLEDGE.md#google-business-profile). Account discovery does not establish location, reviews or performance access. Keep each capability's coverage explicit. The `business.manage` scope also permits writes. The binding must enforce approved reads for this workflow. Profile clicks are not GA4 sessions or completed conversions. The kit's crawl CLI has no Business Profile adapter.

Report the exact failed source and actionable error category (authentication, permission, quota, missing binding or no rows). Do not re-authenticate interactively, change cloud configuration or improvise replacement scripts unless the user explicitly asks.

## SEO Kit crawl binding

When the host project explicitly chooses this kit's live CLI, its SQLite `external_data` table stores queried URL, source, property, period, query timestamp and data. `external_data_coverage` in the JSON report records sample size and missing access. Treat `pagespeed_lab` as laboratory evidence and `crux_field` as field evidence. NEVER: substitute one for the other. GA4 and Search Console performance rows are samples with API row limits, so a URL without a row remains unmeasured.

## Save deliverables

Save keyword-related exports in `keyword-research/`, audit evidence in `audits/`, and standalone performance reports in `reports/DD/MM/YYYY/`. Keep exports beside the deliverable they support.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.

Name report folders by creation date, with zero-padded day/month/year directories: `reports/19/10/2026/search-performance/`. Use the project's timezone, or UTC, and record it. Record the data period separately. Give repeated reports on the same day distinct names.

When Google exports support keyword research, preserve every returned business field using the [keyword research export contract](../seo-optimization/KEYWORD_RESEARCH.md). First-party query performance remains separate from paid competition, CPC, demand volume or organic difficulty collected through other tools. Unsupported metrics stay null with a reason.

For Search Console link-export coverage, see Google's [Links report](https://support.google.com/webmasters/answer/9049606). Its sampled links are distinct from the performance API rows.
