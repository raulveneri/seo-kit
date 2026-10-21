---
name: seo-onpage-checklist
description: On-page and semantic SEO quality gate. Validates search intent, metadata, heading hierarchy, internal linking, topical coverage, YMYL trust needs, and anti-cannibalization. Use when creating or editing pages, landings, or blog posts.
allowed-tools: Read, Grep, Glob
---

# Check and improve on-page SEO

Mark each applicable item PASS/FAIL with evidence. Use unmeasured for missing evidence and N/A with a reason for irrelevant checks. For a failure, give file:line and a concrete fix. Read the host project's conventions in its own context. See "Project conventions" below.

## Blockers (MUST / NEVER)

- [ ] MUST: give each page one dominant search intent. Use relevant terms naturally where they help identify the page's purpose. NEVER: stuff keywords or use density as a target.
- [ ] MUST: make the main topic and main heading clear. Follow the host project's semantic heading convention and review logical nesting for accessibility. A single H1 is a possible project convention, not a universal Google ranking requirement. Multiple H1 elements alone do not establish an SEO failure.
- [ ] MUST: titles are descriptive and distinguish pages. Descriptions summarize each page accurately. Google sets no fixed character limit. Review actual display and treat CLI length thresholds as heuristics.
- [ ] MUST: review missing, duplicate or boilerplate titles and descriptions against page purpose. Use descriptive titles. Google may derive snippets from page content without a meta description. Do not describe a missing description as an indexing blocker.
- [ ] MUST: investigate pages with overlapping purposes using their content and query evidence. Do not consolidate pages solely because they share keywords.
- [ ] MUST: answer the search intent at least as well as the pages in the current results. Avoid thin or duplicate content. Give the answer first, then explain it.

## Further on-page checks (SHOULD)
- [ ] SHOULD: Topical completeness: cover subtopics + associated questions (PAA / related searches) + relevant entities, not just the keyword. Cover what the reader needs without imposing a word-count target.
- [ ] SHOULD: SERP features: format for featured snippet / PAA: a concise self-contained answer, clean definition, list or table, question-shaped H2/H3.
- [ ] SHOULD: Internal linking: important pages are discoverable through relevant crawlable links with descriptive anchors. Review orphaned pages and navigation depth in context. Do not impose a universal click-depth limit.
- [ ] SHOULD: URL: use the host's stable, descriptive URL policy. Review unnecessary complexity without imposing keyword inclusion, transliteration, a depth limit or removal of all parameters. Preserve useful established URLs and verify permanent redirects for intentional moves.
- [ ] SHOULD: Images: descriptive `alt` + meaningful filename for on-page relevance (file optimization → assets-optimization-checklist).
- [ ] SHOULD: E-E-A-T: show real authorship and relevant background where readers expect it. Use honest publish/update dates and source quantitative claims. Assess the quality of the main content and suitability of experience or expertise for its purpose. Do not treat a bio or credentials as a ranking shortcut.
- [ ] SHOULD: YMYL: assess the page's potential to cause significant harm if inaccurate (health/safety, financial stability, civic or societal welfare). For clear YMYL advice, verify against authoritative sources and expert consensus. Check suitable expertise, responsibility and conflicts of interest. First-hand experience can support experience-sharing, but does not replace expert advice. See KNOWLEDGE §2.
- [ ] SHOULD: AI-assisted content: manually verify factual claims and generated metadata before publishing. Disclose how automation was used when readers would reasonably need that context. Before expanding a template, identify the distinct reader task and original contribution of each page. Review a representative sample. Avoid scaled pages with little original value. Rater guidance is not a direct ranking formula.
- [ ] SHOULD: Freshness: refresh and re-date pillar / changing-topic content honestly. NEVER: fake dates.
- [ ] SHOULD: FAQ: add a visible question-and-answer section when it helps readers resolve distinct questions. Google retired FAQ rich results in May 2026. Do not add FAQPage markup for that retired benefit. Review other consumers before removing existing markup. Google AI features require no special markup.

## Page-level content review

For a blog, guide, review, landing page, product or other substantive page, load [CONTENT_REVIEW.md](CONTENT_REVIEW.md). Record the common criteria and applicable page-type tasks separately, with evidence and proposed actions. Use the `pages`/`items` contract when supplying `onpage.intent_review` evidence to the CLI. Do not award all content-review points from one summary verdict or infer that a reviewed page covers unreviewed pages.

## Conditional specializations

Apply only the blocks matching the host site's declared business model, languages and current task. Mark non-applicable blocks N/A. Missing required evidence is unmeasured, not PASS. These are contextual review items, not new CLI checks or scoring weights. Sources and rationale are in KNOWLEDGE, "Conditional specialization evidence".

### Local service and location pages
- [ ] Confirm each location/service page describes a real operation and useful local information: services available, contact details, hours and service area where applicable. Do not invent offices or multiply near-identical city pages solely to capture queries.
- [ ] Compare displayed identity and location details with the declared business record. Route external profile, citation and review checks to `seo-offpage-checklist`. Keep page-content findings here.

### Ecommerce categories and products
- [ ] Match category and product pages to their distinct search tasks. Check descriptive category navigation and useful product specifications, images and purchasing information. Flag copied or empty templates for review without imposing word-count floors.
- [ ] Check that the selected variant, price, currency and availability are clear and consistent with the actual offer. Compare shipping/return information where provided. Do not fabricate identifiers, stock, reviews or policies.
- [ ] Record the business decision for temporarily unavailable and discontinued products, useful alternatives and retained customer information. Send status, redirect, canonical and sitemap verification to the technical checklist rather than automatically removing or redirecting every unavailable product.

### International and multilingual content
- [ ] Check that each locale's main content and navigation use the intended language and serve the declared audience. Assess local terminology, currency, offer availability and contact details where relevant. Language variants do not automatically require different countries.
- [ ] Review equivalent pages for untranslated templates, misleading locale links and content gaps. Use locale-specific query evidence when available. Do not assume the same intent or keywords in every market. Technical access and annotations belong to `seo-technical-checklist`.

### Content continuity during migrations
- [ ] Compare priority source and destination pages for retained purpose, useful content, metadata and internal-link context. Document intentional consolidations and removals. Do not treat every content difference as a regression. Technical URL mapping and post-move verification belong to the technical checklist.

## Match the page type to search intent
Deduce intent from the live SERP and, when available, the site's Search Console page-and-query data through its declared binding. Match the page type to the observed intent:

| Intent | Query shape | Page type / format |
|---|---|---|
| Informational | "what is X", "how X works" | Guide/blog, answer-first, depth, E-E-A-T |
| Navigational | brand or entity name | The named entity's page, with limited room for on-page changes |
| Commercial | "best X", "X vs Y", "X reviews" | Comparison, criteria, tables, pros/cons |
| Transactional | "buy X", "hire X near me", "X pricing" | Landing: proposal, proof, CTA, price/range |

Investigate a mismatch between the page task and observed results. Record the query, market, date and mixed intents. Compare a different target or page approach only when the evidence supports it. One observed result set does not justify automatically replacing a useful page.

## Scope and limits
- Keyword volume/difficulty without data: produce the plan and ask for the source (Search Console / MCP / user export). NEVER: invent search figures.
- Core Web Vitals / canonical / indexing → seo-technical-checklist. Backlinks / authority / NAP → seo-offpage-checklist. AI-citation / GEO → seo-geo-checklist.
- **Brand/aesthetic rules are not SEO and do not belong here:** title separator style, dash bans and CTA voice/tone come from the host project, if declared. Google lists several separator styles. Follow the project's copy convention without claiming a ranking gain.

## Project conventions
This skill is project-agnostic. Read the host project's `AGENTS.md` and declared context for its URL policy, target intents and keywords, metadata implementation, internal-link structure and indexability rules. Do not assume any route, page hierarchy, helper or framework.

## When you need more detail
The gate and advanced section above cover common checks. For the reasoning behind these checks (reader intent, E-E-A-T, metadata, links, follow-up and Google technical references) open the sibling `KNOWLEDGE.md`.

---
Sources: Google Search Essentials <https://developers.google.com/search/docs/essentials> · Titles and snippets <https://developers.google.com/search/docs/appearance/title-link> · Creating helpful content / search intent <https://developers.google.com/search/docs/fundamentals/creating-helpful-content> · Links best practices <https://developers.google.com/search/docs/crawling-indexing/links-crawlable>

## Save deliverables

Save keyword research, clusters and keyword-to-page maps in `keyword-research/`. Save on-page audit reports and evidence in `audits/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.

For keyword research and enrichment, follow the [keyword research contract](../seo-optimization/KEYWORD_RESEARCH.md). Include keyword, monthly volume, search intent, paid competition and CPC first, then all additional returned fields with source, scope and units. Preserve complete structured exports and sanitized raw responses. Do not invent missing metrics. Link content proposals under `proposals/<type>/` to the corresponding research records.
