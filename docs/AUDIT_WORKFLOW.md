# SEO/GEO audit workflow

Open the website project and read its `AGENTS.md`. Use its declared domain and keep credentials and reports in its approved locations. Ask `seo-audit` to coordinate the steps below, or run them yourself.

For an overall optimization task, the [SEO optimization workflow](../.agents/skills/seo-optimization/SKILL.md) uses this audit as evidence alongside project goals and opportunities. It compares proposals and recommends one or more paths. If several viable strategies remain, the user chooses before dependent implementation. A single reasonable path needs no artificial choice. An audit-only request does not require a separate strategy exercise.

## 1. Set the scope

Record the HTTPS origin, deployed environment, audit date, build command and HTML location. Include the relevant templates, languages and critical pages. Use the project's declared queries, markets and data connections. Do not invent search volume or competitors. Record the previous report, comparison period and scope changes.

Without a compiled site, offer `100`, `500` or `unlimited` URLs and default to `100` when no choice is given:

```bash
mkdir -p /path/to/project/audits
npm run audit:live -- --url https://example.org/ --crawl-limit 100 --database /path/to/project/audits/crawl.sqlite --format json --output /path/to/project/audits/audit-live.json
```

Set request, time, disk, response-size and rate limits. `--resume` requires matching settings. Continue with partial coverage when external sources are missing and keep those gaps visible.

## 2. Capture the baseline

Run the project's declared build, then run from the kit:

```bash
mkdir -p /path/to/project/audits
npm run audit -- --site /path/to/project/dist --base-url https://example.org --format json --output /path/to/project/audits/audit-initial.json
```

Save the project revision, date, command and scope with the report. Build mode checks HTML, metadata, links, robots and sitemaps. Scoring version 2 reports measured coverage relative to applicable checks. Build-only coverage varies with the evidence. See [SCORING.md](SCORING.md). Live mode crawls public same-origin HTTPS, checks robots and HTTP responses, and optionally renders with `--render auto|always|never`.

Inspect `crawl_complete`, warnings, routes and `unmeasured` checks. A truncated sample is not a complete site audit. Query SQLite with `npm run audit:query -- query --database <db> --table issues` and export JSON or CSV as needed.

## 3. Collect and review external evidence

Use only project-declared sources. Every evidence entry needs a traceable `source`, ISO `date`, `period`, same-origin `scope` and review reasoning. Store exports or captures with the audit in `audits/` inside the selected project. Keep personal data out of the report.

| Check | Evidence and passing criterion | Missing evidence |
| --- | --- | --- |
| `technical.indexing` | Search Console URL Inspection for the sample: indexability, declared vs Google-selected canonical and coverage errors. Pass only when reviewed cases meet the criterion and sample scope is recorded. | `unmeasured` |
| `technical.http` | Deployed responses, status, redirect chains, served canonical, headers and robots/sitemap consistency. Pass when the documented scope has no relevant failures. | `unmeasured` |
| `onpage.intent_review` | Current queries/SERPs, content, route-intent map and cannibalization. Record market, language and sample. Pass when pages meet intent without conflicting targets. | `unmeasured` |
| `geo.review` | GEO and agentic-search checks: bot access, effective Search generative AI inclusion including inherited choices, accessible content and reviewed claims. Account evidence is separate from the crawl. Do not promise citations or AI traffic. | `unmeasured` |
| `performance.lcp` | Field p75 for the declared scope in ms. Pass at 2500 or below. | `unmeasured` |
| `performance.inp` | Field p75 in ms. Pass at 200 or below. | `unmeasured` |
| `performance.cls` | Unitless field p75. Pass at 0.1 or below. | `unmeasured` |
| `offpage.review` | External link evidence, referring-domain relevance, anchors and risks. NAP only where applicable. Pass when the reviewed sample has no relevant failures. | `unmeasured` |

These are the CLI's existing field thresholds. Retain source, date and collection period for every measurement. A lab score is not a field record. Connect missing sources with [seo-mcp-setup](../.agents/skills/seo-mcp-setup/SKILL.md), and consult [USAGE.md](USAGE.md#data-connections) for API flags.

For AI visibility, review an authorized export of the [Generative AI performance report](https://support.google.com/webmasters/answer/16984139) and read-only evidence of the [Search generative AI control](https://support.google.com/webmasters/answer/16908024). These Google references were checked 2026-10-21. The existing CLI does not collect either surface. Preserve impression aggregation and report limits. Do not infer AI clicks or conversions. Missing access stays unmeasured, and a review does not authorize account changes. Use the [optimization evidence reference](../.agents/skills/seo-optimization/KNOWLEDGE.md) to check feature availability and official rollout dates before interpreting traffic changes.

Live HTTP checks pass only when the crawl completes within its limits. `--crux` can supply origin field p75. `--gsc-property` can supply indexing results when all crawled pages have usable inspections. Origin data does not describe every URL. Google's inspection reflects the indexed version. Backlink CSV counts stay unmeasured for quality until reviewed. Explicit `--evidence` overrides automatic results and must justify that override.

Technical indexing and HTTP reviews use `status: "pass"|"fail"` and `detail`. Content requires the [page-level review record](../.agents/skills/seo-onpage-checklist/CONTENT_REVIEW.md). GEO and off-page require the item-level evidence in [SCORING.md](SCORING.md). Missing items and unreviewed pages remain unmeasured. Core Web Vitals require numeric `value` and `kind: "field_p75"`. The CLI applies thresholds and rejects a manual pass in their place.

```json
{
  "checks": {
    "technical.indexing": {
      "status": "fail",
      "detail": "The inspected /guide/ URL has a different Google-selected canonical. Sample: 12 priority URLs",
      "source": "Search Console export 2026-10-14",
      "date": "2026-10-14",
      "period": "indexed state queried 2026-10-14",
      "scope": "https://example.org"
    }
  }
}
```

## 4. Report and prioritize

```bash
mkdir -p /path/to/project/audits
npm run audit -- --site /path/to/project/dist --base-url https://example.org --evidence /path/to/project/audits/evidence.json --format json --output /path/to/project/audits/audit-final.json
```

Include scope, date, sources, scoring version, measured score and coverage, checklist bounds, category/page assessments, critical failures, pass/fail/unmeasured/N-A findings, affected URLs/files, limits and actions. Explain that the bounds concern unresolved checklist evidence and do not predict rankings. 100% coverage means all weighted criteria have evidence. It does not mean every search factor was measured or that supplied reviews are correct. Compare scores only under a consistent rubric and scope.

Prioritize technical/on-page MUST/NEVER failures, then demonstrated user/search problems, then SHOULD opportunities. Assign an owner, concrete change, supporting evidence and verification method to each action. Missing data creates a measurement task. Strategy and rule changes require human review under the change contract.

## 5. Fix and measure again

For live crawls, the [before/after guide](FOLLOW_UP.md) provides a complete snapshot and comparison sequence, interpretation of output fields and URL migration mapping.

Send implementation work to its project owner. Use [seo-pagespeed-optimizer](../.agents/skills/seo-pagespeed-optimizer/SKILL.md) for iterative performance and accessibility fixes. The technical audit agent remains read-only.

After approved fixes, rebuild, refresh stale evidence and run:

```bash
mkdir -p /path/to/project/audits
npm run audit -- --site /path/to/project/new-build --base-url https://example.org --evidence /path/to/project/audits/current-evidence.json --baseline /path/to/project/audits/audit-final.json --format json --output /path/to/project/audits/audit-followup.json
```

Compare checks measured in both reports. Failures are matched by criterion and location, not root cause. Verify persistent findings. Score differences are shown only with equal coverage and routes. Changes in language, source or period can still limit comparability. Close an action when fresh evidence confirms the fix, and retain residual risks, missing checks and the next review date.

For URL-level crawl comparisons, run `npm run audit:query -- compare --before <old-db> --after <new-db> --format json`. Use `--url-map <json-file>` for migrations. Check `scope_comparable` before interpreting additions and removals: incomplete crawls, different budgets or missing cross-origin maps can reflect scope rather than site changes.

## Changelog

- 2026-10-21: Added scoring-version-2 item-level review and reporting. Numerical comparisons require matching rubrics and measurement sets.

- 2026-10-21: Clarified manual AI inclusion evidence, generative impression reporting and the existing CLI's collection limits. Scoring and automated coverage are unchanged.
