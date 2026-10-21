---
name: seo-optimization
description: Develop and execute a website-specific SEO and GEO optimization plan. Use for overall SEO improvement, new-site planning, opportunity discovery or comparing strategic proposals, from critical evaluation, one or more recommendations and user choice between viable paths through authorized implementation and measurement.
---

# Plan and deliver SEO and GEO optimization

Start in the dedicated project folder for the selected website or client. It can hold website source or just SEO work. Keep its context and deliverables together. When switching clients, resolve the new target folder before using context or saving files. Ask for the target if it is unclear.

Read the website project's `AGENTS.md`, context and existing decisions. Identify its purpose, audience, market, language and priority user journeys. Check whether the site is new or already live, what constrains the work and what evidence is available. Ask for missing information only when it changes the decision. Continue independent work and state your assumptions.

An audit is an evidence source, not a prerequisite for every optimization task. For a new site or a focused request, inspect the relevant content, routes, templates and implementation directly. Use `seo-audit` when a broader baseline is useful. Missing analytics does not prevent a provisional plan, but its opportunities and expected effects remain hypotheses.

## Check current evidence

Read [KNOWLEDGE.md](KNOWLEDGE.md) when recommendations depend on current Google behavior, feature availability or an update. Verify the affected official documentation and rollout record, retain dates and scope, and distinguish observed outcomes from hypotheses. Reconcile conflicting versions before implementation. Do not assume an old checklist or a connected API covers a newly introduced report.

## Keyword research

For keyword discovery, clustering or enrichment, read [KEYWORD_RESEARCH.md](KEYWORD_RESEARCH.md) and follow its full collection and export contract. Gather every available business field from the authorized tool response, not just the summary metrics. Keep keyword, monthly volume, search intent, paid competition and CPC first, then organic difficulty, source/scope metadata and all additional fields. Save CSV, typed JSON, sanitized raw responses and available time-series/SERP sidecars in `keyword-research/`. Missing access or metrics remain explicit. Paid competition is not organic difficulty. Keep additional collection within the authorized scope and budget.

## Build and compare proposals

Identify opportunities as well as defects: unmet search intent, useful page coverage, route relationships, internal links, crawl/indexing problems, performance, assets and AI-search readiness where relevant. Inspect existing pages before proposing new ones. Require external link evidence for off-page conclusions.

Develop distinct alternatives only where there is a real choice, such as improving an existing page versus creating a separate page for a distinct intent. Include keeping the current approach when it is defensible. Do not invent alternatives just to fill a table or assume more pages are better.

For each credible option, state:

- The problem or opportunity, affected pages/templates and intended user/search outcome.
- Supporting observations and sources, assumptions, confidence and evidence gaps.
- The concrete change, dependencies, effort and maintenance cost.
- The expected benefit, labeled as a hypothesis unless measured, and risks to existing traffic, intent overlap, usability, accessibility and implementation.
- A way to verify the result and a condition for revising or stopping the approach.

Compare options against the project's goals and constraints. Challenge the initial request when evidence suggests a weaker outcome. Reject unsupported or disproportionate proposals and explain the trade-off. Recommend one or more paths with reasons and explain which conditions favor each. When several viable strategies remain, present them for the user to choose with their own judgment. Do not silently select one on the user’s behalf. Avoid fabricated ranking, traffic, revenue, volume or difficulty forecasts and arbitrary numerical priority scores.

## Select and implement

Record the viable paths, recommendations, alternatives rejected and why, assumptions and next actions in `proposals/<type>/` inside the selected project. Keep website-specific plans outside this kit.

- If there is only one reasonable path, explain why it is the suitable option. Do not invent alternatives or request a choice that does not exist. Continue implementation within the existing authorization.
- If several viable paths exist, show their trade-offs and recommend one or more where justified. Ask the user to choose and wait for that choice before implementing work that depends on it. This applies even when the general request asks for the best approach: a recommendation does not replace the user's selection between viable strategies. Continue useful independent analysis while waiting.
- Group compatible improvements into the same path. A list of routine fixes is not automatically a set of competing strategies. After the user selects a path, resolve routine implementation details within that path without repeatedly asking for approval.
- A proposal-only request ends with reviewable options and recommendations. External actions, spending and publication still require the relevant authorization.

Route work through the available specialists and skills:

| Work | Execution path |
| --- | --- |
| Baseline and crawl evidence | `seo-audit` |
| Intent, metadata, headings and internal links | `seo-onpage` and `seo-onpage-checklist` |
| Technical diagnosis | `seo-technical` and `seo-technical-checklist`, with implementation by the project's owner |
| Performance and accessibility regressions | `seo-pagespeed-optimizer` and `assets-optimization-checklist` |
| Link-profile evidence | `seo-offpage`, preserving its read-only boundary |
| AI-search review | `seo-geo-checklist` and `agentic-search-readiness` |
| Data access and first-party evidence | `seo-mcp-setup` and `google-data` |

These are routing instructions, not a requirement to spawn agents or run every check. Apply only the relevant workflows. Preserve specialist read-only boundaries. Use the owning implementation role for code changes. Keep account mutations, spending, deployment and publishing within the user's authorization.

## Assess checklist evidence

For site or page scoring, use the kit's versioned audit rubric and the `seo-onpage-checklist/CONTENT_REVIEW.md` record. Include applicable blog, guide, review, landing or product tasks. Report score with coverage, unresolved checks, category/page scope and critical failures. Treat checklist bounds as accounting for missing evidence, not ranking forecasts. Do not change category weights to make a result look better, copy one page's review to unreviewed pages or compare scores across different rubric/measurement sets.

## Verify and adapt

Run the consuming project's relevant build and checks. Compare fresh evidence under comparable conditions and distinguish immediate implementation checks from later search or field-data outcomes. Track the actual objective alongside audit coverage or diagnostic scores. Revise a proposal when new evidence contradicts its assumptions.

Report the objective and scope, evidence gaps, compared options, recommended path or paths, rationale and the user’s selection when applicable, changes implemented or ready for review, validation results and follow-up measurement. If implementation was requested, do not stop at a plan while authorized work can still be completed. Do not claim an outcome that has not been measured.

## Save deliverables

Save keyword research and its exports in `keyword-research/`, audit evidence in `audits/`, compared proposals and implementation plans in `proposals/<type>/`, and standalone progress reports in `reports/DD/MM/YYYY/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.

Group proposals by type, such as `proposals/articles/`, `proposals/guides/`, `proposals/landings/`, `proposals/technical/` or `proposals/strategy/`. Keep decisions and implementation tracking with the corresponding proposal. Link related proposals instead of duplicating them.

Name report folders by creation date, with zero-padded day/month/year directories: `reports/19/10/2026/search-performance/`. Use the project's timezone, or UTC, and record it. Record the data period separately. Give repeated reports on the same day distinct names.
