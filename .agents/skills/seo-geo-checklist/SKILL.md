---
name: seo-geo-checklist
description: Google AI-search quality gate (AI Overviews and AI Mode). Reviews Googlebot access, indexing and snippet eligibility, published file hygiene, readable answers, identity and freshness. Use when creating/editing content that should be cited by generative engines, or when touching llms.txt / robots / AI-bot access. Loaded by seo-onpage and seo-technical.
allowed-tools: Read, Grep, Glob, WebFetch
---

# Check GEO and AI-search readiness

GEO (Generative Engine Optimization) helps you prepare content for citation in AI answers. Mark each item PASS/FAIL, with file:line and a fix.

## Blockers (MUST / NEVER)

- [ ] MUST: compare served `robots.txt`, server and CDN controls with the project's intended access policy. For Google AI Overviews and AI Mode, check Googlebot, indexing, snippet eligibility and the effective Search generative AI control in Search Console, including inherited choices. Missing account evidence stays unmeasured. An audit does not authorize changing the control. `Google-Extended` controls specified Gemini uses and does not govern Google Search. See KNOWLEDGE section 2.
- [ ] MUST: if the site serves `/llms.txt`, check that its contents and links are current. This is file maintenance, not evidence of a citation benefit. See KNOWLEDGE section 3.
- [ ] MUST: verify that Google can access important text and links. Prefer initial HTML where practical, and inspect rendered content when JavaScript is involved.
- [ ] MUST: verify substantive claims and retain their supporting evidence. Do not invent search penalties or citation effects for an unsupported claim.

## Passage-level citability
- [ ] SHOULD: answer the reader's question clearly before adding detail. Choose a passage length that serves the question. No fixed sentence count establishes citation eligibility.
- [ ] SHOULD: use descriptive headings. Phrase them as questions when that reflects the reader's task. Add a visible FAQ section only when distinct, real questions remain after the main content. Google AI features require no special markup. Google retired FAQ rich results in May 2026. Do not propose FAQPage markup for that retired benefit. Verify other feature guides before proposing a rich result.
- [ ] SHOULD: concrete data, figures with source and date, clean definitions with evidence readers can check.
- [ ] SHOULD: lists and tables for structured facts when they make the information easier to understand.

## Entity and brand signals (SHOULD)
- [ ] SHOULD: consistent brand/author entity (Person/Organization/LocalBusiness schema, NAP, sameAs to profiles). Match markup to visible, accurate information.
- [ ] SHOULD: brand mentions + co-occurrence with the site's target topics (and place, if local) on the site itself and off it.
- [ ] SHOULD: freshness: honest `updatedDate`. Update dates only when the content has actually changed.

## Measurement

- [ ] Use the Search Console Generative AI performance report or an authorized export for the impressions it exposes. Preserve dates, dimensions and aggregation. Do not infer clicks, CTR or conversions, treat an absent report as zero, or assume the kit's Search Analytics adapter exposes this dataset.
- [ ] Check the current Google guidance before recommending an AI-specific tactic. Do not recommend artificial mentions, hidden instructions or scaled low-value query-variation pages to manipulate generative answers.

## Reviewed scoring evidence

For the CLI's `geo.review` group, provide an `items` object with `access`, `claims`, `identity` and `measurement`. Each item records `status` (`pass`, `fail`, `unmeasured` or `not_applicable`) and concrete `detail`. Keep `source`, ISO `date`, `period` and same-origin `scope` on the group. An unavailable account observation or measurement stays unmeasured. A blanket pass does not earn item-level credit. See the sibling KNOWLEDGE for criteria.

## Scope and limits
- Doesn't cover classic ranking (see seo-onpage / seo-technical). GEO is complementary, not a substitute.
- Don't claim an engine "cites" something without verifying it (WebFetch to the surface if you check).
- Use `agentic-search-readiness` for access controls across the site, optional interfaces and repeatable visibility observations. This checklist reviews an individual page. Neither workflow can establish future citations.

## Project conventions
Honor the **host project's own bindings** from its `AGENTS.md`: where `/llms.txt` and robots are generated, the AI-bot allow/block decision, the brand/author entity + NAP source, and the target topics. Do not hardcode a project's paths, entity names, or topics here.

## When you need more detail
Read the sibling `KNOWLEDGE.md` for Google eligibility, crawler access, published files and observation limits.

---
Sources: Google *AI features and your website* <https://developers.google.com/search/docs/appearance/ai-features>.

## Save deliverables

Save GEO audit reports and evidence in `audits/`. Save standalone AI-visibility tracking reports in `reports/DD/MM/YYYY/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.

Name report folders by creation date, with zero-padded day/month/year directories: `reports/19/10/2026/search-performance/`. Use the project's timezone, or UTC, and record it. Record the data period separately. Give repeated reports on the same day distinct names.
