# Shared SEO/GEO runtime

Use the installed skills and agents when a task concerns classic SEO, technical SEO, off-page SEO, GEO, AI-search visibility, first-party search data.

Select the matching workflow from the task's intent even when the user does not mention SEO Kit or a skill name. General requests to improve search visibility or organic traffic use `seo-optimization`. Focused indexing, content, backlink, AI-search or performance requests use the corresponding checklist. Do not load the kit for unrelated tasks. If the host cannot delegate to specialist agents, follow their canonical workflows in the current session without assuming delegation is available.

Always read the current project's own `AGENTS.md` and declared context before acting. Project facts belong to the project. NEVER: infer a domain, brand, framework, route, analytics property or command from this shared toolkit. If required context or data is absent, report the gap instead of inventing it.

Treat every quantitative SEO claim as measured data: cite its source, date and time range. Keep SEO/GEO advice separate from copy style, visual design and brand preferences.

For overall website SEO optimization, use `seo-optimization` to identify opportunities, compare proposals, recommend one or more approaches and carry authorized changes through validation and follow-up. Use `seo-audit` for audit evidence. New-site planning may proceed from declared requirements. Absent analytics stays an explicit evidence gap.

When several viable optimization strategies remain, present the trade-offs and recommendations and let the user choose before implementing dependent changes. With one reasonable path, explain it and proceed within existing authorization. Do not invent alternatives or ask again about routine details within a selected path.

## Checklist evidence

For website or page assessments, use the installed checklists and the page-type content review record. Report the scoring version, measured score, coverage, unresolved items and critical failures together. Missing evidence is unmeasured, and N/A needs a reason. A high partial score does not establish full optimization or predict rankings. Numerical before/after comparisons need the same rubric, scope and measured/applicable checks.

## Generated files

Use a dedicated project folder for each website or client. The user selects that folder as the active project in the assistant. Keep each website's context and generated files together there, including when several clients are being worked on. When switching clients, resolve the newly selected project again and use only its context and data. If no target folder is clear, ask the user to open or identify it before creating deliverables.

Resolve the selected client or website project's absolute root from the active workspace and its declared context before writing. The project may be a client SEO working folder without application source or Git. Do not substitute the SEO Kit checkout, the shell working directory used to run kit commands, a website URL or a sibling client directory. If the selected root is ambiguous, ask for it before creating files.

Create destination directories inside that root when first needed:

| Deliverable | Directory relative to the selected project |
| --- | --- |
| Keyword research, query exports, clusters and keyword-to-page maps | `keyword-research/` |
| Audits, crawl databases, reviewed evidence, performance/accessibility measurements and audit comparisons | `audits/` |
| Proposals grouped by type, selected plans and implementation tracking | `proposals/<type>/` |
| Standalone search-performance, AI-visibility and progress reports | `reports/DD/MM/YYYY/` |

Use proposal types such as `articles`, `guides`, `landings`, `technical` or `strategy`. Add another descriptive type when justified. Save each proposal with its evidence, decision status and subsequent implementation tracking in `proposals/<type>/<YYYY-MM-DD-topic>/`. Use a strategy proposal to link related work across content types. Do not move or rename existing client deliverables without an explicit migration request.

For standalone reports, `DD/MM/YYYY` means zero-padded day, month and four-digit year as nested directories, for example `reports/19/10/2026/`. Use the project's declared timezone, or UTC if none is declared, and record it. The folder date is the report creation date. Record the measurement period separately. Group report types within that date, such as `reports/19/10/2026/search-performance/`, and add a time or run suffix for repeated reports without overwriting earlier results. Supporting audit reports remain with their audit in `audits/`.

Keyword research follows the comprehensive record and export contract in the [keyword research contract](../skills/seo-optimization/KEYWORD_RESEARCH.md): core metrics first, all additional available business fields preserved, explicit source/scope/units, raw responses and a structured export alongside the readable summary. Use connected tools within the authorized scope and budget. Missing metrics remain null with a reason.

Keep supporting exports beside the deliverable they support. For another deliverable type, create a descriptive kebab-case directory in the same project. Create only directories needed for the current task. Reuse existing directories and group separate runs by a dated filename or subdirectory, such as `audits/2026-10-19-baseline/`. Preserve earlier results. Use a distinct run name when a destination already exists. Resume an existing crawl only when requested or continuing an interrupted run with matching settings.

Resolve paths, including symlink targets, and ensure destinations stay within the selected project and outside the kit checkout. Create the directory before invoking CLI commands that require an existing parent. Pass absolute database, input and output paths even when running commands from the kit directory. Store generated deliverables outside published asset and build directories. Website source edits still use the project's actual source paths.

Save substantive deliverables to these files as well as summarizing them in chat, and report their paths. Technical and off-page agents may write their audit artifacts while keeping website source and configuration read-only. NEVER: place credentials or tokens in reports. If a destination cannot be written, report the error and ask for a valid location inside the selected project. Do not silently fall back to the kit or another directory.

For CLI crawls, HTML retention defaults to `--store-html none`. Use `raw`, `rendered` or `both` when retained source is needed for the requested task and explain the choice. Keep SQLite files local in the client's `audits/` folder. Credential filtering is bounded. Retained page text and identifiers may contain personal data. Use the filtered `audit:query share` command when preparing data to share, review its URLs, and minimize evidence sent to an AI assistant or external provider. Retention stays off until a duration is configured. Protect important crawls and preview deletion before applying it. Existing databases and exports are not retroactively sanitized. See `docs/USAGE.md` in the kit for the controls and their limits.
