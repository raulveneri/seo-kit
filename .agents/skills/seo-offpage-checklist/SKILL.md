---
name: seo-offpage-checklist
description: Quality gate for off-page analysis (link profile, authority, brand mentions, and NAP). ANALYSIS and report only. Requires an authorized backlink export or a declared Moz/DataForSEO binding. Use when asked to audit backlinks, authority, or local brand consistency.
allowed-tools: Read, WebSearch, WebFetch
---

# Review off-page SEO

Mark each item PASS/FAIL and cite the data source for every finding. Write an actionable report. Keep website source read-only and never invent metrics.

## Blockers (MUST / NEVER)

- [ ] MUST: every quantitative claim (referring domains, provider metrics, anchor observations) cites its source and date. NEVER: invent backlink metrics: if there's no data, ask for the source (GSC / Moz / DataForSEO / authorized export / user export).
- [ ] MUST: when the site represents a local business, compare NAP (name, address, phone) with its declared business identity and any `LocalBusiness` schema. NEVER: report a NAP as "correct" when sources conflict. Mark N/A when the site has no applicable physical business identity.
- [ ] MUST: investigate suspected link spam using source-page evidence. Consider disavow only when a considerable number of spammy, artificial or low-quality links caused, or are likely to cause, a manual action. Try removal first and escalate the evidence for review. See KNOWLEDGE section 3.
- [ ] NEVER: recommend buying links, PBNs, mass exchanges, or any scheme against the engine's spam policies.

## Analysis (SHOULD)

- [ ] SHOULD: Record anchor-text patterns and inspect their context. Do not use a universal branded/exact-match ratio as a pass rule.
- [ ] SHOULD: Review relevance, source-page context and evidence of manipulative creation. Link counts alone do not establish quality.
- [ ] SHOULD: Compare dated samples only when coverage is comparable. Investigate changes without assuming a particular growth rate is natural.
- [ ] SHOULD: Record genuine unlinked mentions separately from backlinks. Do not promise outreach success or ranking gains.
- [ ] SHOULD: Compare relevant source pages in authorized exports to identify possible omissions or opportunities. Do not treat every other site's link as suitable to pursue.
- [ ] SHOULD: Keep provider estimates separate from Google data and preserve their definitions and limits.

## Conditional local business review

Apply when the project declares a local business. Otherwise mark N/A. Extend the existing NAP check rather than repeating it. Missing profile access or exports stay unmeasured. This block is analysis only and adds no CLI score. Sources and rationale are in KNOWLEDGE, "Conditional specialization evidence".

- [ ] Compare the declared Google Business Profile with the real business and website: applicable verification state, primary/additional categories, address or service area, phone, website, regular/special hours and services where available. Record the profile URL, review date and evidence. Flag inaccurate information without editing the account.
- [ ] Inspect review-request flows for selective solicitation and incentives. Flag routing only satisfied customers to Google while withholding that option from dissatisfied customers. Google prohibits discouraging negative reviews and selectively soliciting positive ones. Keep account actions outside this review. See KNOWLEDGE section 5.
- [ ] Review a dated sample of genuine reviews and owner responses for recurring service issues and response gaps. Distinguish observation from sentiment interpretation. Do not promise that a response or review count will improve ranking.
- [ ] For multiple locations, reconcile each profile and landing page with its own real operation. Escalate duplicate or conflicting records for review. Do not create fictitious locations.
- [ ] Interpret local visibility with its query, observation location and date. Google describes relevance, distance and prominence as key factors. Do not compare map positions from different locations as though they were a single site-wide rank.

## Reviewed scoring evidence

For the CLI's `offpage.review` group, provide an `items` object with `link_evidence`, `link_quality` and `identity`. Each item records `status` (`pass`, `fail`, `unmeasured` or `not_applicable`) and concrete `detail`. Keep `source`, ISO `date`, `period` and same-origin `scope` on the group. Missing exports leave link checks unmeasured. Explain an irrelevant local identity check without inventing a business. A blanket pass does not earn item-level credit. See the sibling KNOWLEDGE for criteria.

## Scope and limits
- Does not edit the site or create links. Produces an actionable report only.
- On-page/technical → the other seo-*-checklists.

For a declared DataForSEO MCP binding, use [the connection and query procedure](../seo-mcp-setup/DATAFORSEO.md) to verify Backlinks access, target scope, filters and pagination within the agreed budget. Preserve provider definitions and sample limits. A successful response alone does not complete the qualitative `offpage.review` evidence.

## Project conventions
Read the host project's `AGENTS.md` and declared context for its business identity, applicable `LocalBusiness` schema, competitor set and entity names. Do not assume any of these exists.

## SEO Kit crawl binding
If the host project authorizes the kit's Moz query or provides a normalized CSV, inspect the recorded coverage and period before drawing conclusions. The CLI's Moz result is a capped sample in `external_data`, and the CSV path is summarized in `backlink_summary`. Neither alone proves a complete link profile or a quality verdict. Keep `offpage.review` unmeasured until a human reviews relevance and risk.

## When you need more detail
Start with this checklist. For more detail (authority signals, healthy profile, anchor text, reclamation, local citations, spam detection, disavow, engine link policies) open the sibling `KNOWLEDGE.md`.

---
Sources: Google spam policies <https://developers.google.com/search/docs/essentials/spam-policies> · Link best practices <https://developers.google.com/search/docs/crawling-indexing/links-crawlable>

## Save deliverables

Save off-page audit reports and supporting exports in `audits/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.
