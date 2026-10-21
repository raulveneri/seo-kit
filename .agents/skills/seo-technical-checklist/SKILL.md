---
name: seo-technical-checklist
description: Technical SEO quality gate. Validates crawlability, indexing, canonical, trailing-slash consistency, sitemap/robots, Core Web Vitals (LCP/INP/CLS), headers, and rendering. Use before merging changes that touch URLs, meta, redirects, sitemap, robots, or performance.
allowed-tools: Read, Grep, Glob, Bash
---

# Check technical SEO

Mark each item PASS/FAIL. For every failure, give file:line and a fix. Any failed blocker invalidates the result. Get the build tool, host and paths from the host project's context. See "Project conventions" below.

## Blockers (MUST / NEVER)

- [ ] MUST: review canonical signals against the intended preferred URL, including deliberate duplicate alternatives. Flag conflicting declarations and redirecting targets. Do not require self-canonicals on every URL or treat an absent canonical as automatic exclusion from Google.
- [ ] MUST: one consistent trailing-slash policy site-wide. Canonical, `og:url`, and every sitemap entry emit the same form the server serves (so they never point at a 301/308 redirect).
- [ ] MUST: remove `noindex` from pages intended for indexing. For pages that should stay out of the index, use `noindex` in metadata or headers. NEVER: use `Disallow` for this purpose, because robots controls crawling.
- [ ] MUST: evaluate effective Googlebot groups and path rules for pages intended for Search. Check specific-agent rules and allow/disallow precedence. A robots file or sitemap declaration is not universally required. Do not fail a site merely for their absence. Flag an accidental production block against the declared indexing policy.
- [ ] MUST: check internal destinations and intentional redirects against the route policy. Flag broken targets, loops and avoidable chains. Permanent moves can use 301 or 308. Preserve useful old-to-new mappings. Intentional removals may correctly return 404 or 410.
- [ ] MUST: verify that Google can access indexable text, links and metadata. Prefer initial HTML where practical and test rendered output when JavaScript is involved. Do not assume JavaScript content is unindexable.

## Core Web Vitals (MUST, web.dev good thresholds, field p75)
- [ ] MUST: LCP ≤ 2.5 s. NEVER: apply `loading="lazy"` or a scroll-reveal that hides the above-the-fold LCP image/element at paint. Set dimensions and verify whether priority or preload improves the measured resource path.
- [ ] MUST: CLS ≤ 0.1. Set image dimensions or aspect ratios and keep self-hosted fonts from shifting the layout. NEVER: inject content above content already painted.
- [ ] MUST: INP ≤ 200 ms. Investigate slow interactions and main-thread work in traces. Test third-party loading changes against required behavior and consent.

## Advanced technical (SHOULD)
- [ ] SHOULD: Sitemap hygiene: include only canonical, indexable URLs and use honest `lastmod` dates. Exclude noindexed, thin and redirecting pages. Split files above 50,000 URLs or 50 MB.
- [ ] SHOULD: Redirects: verify appropriate permanent redirects (301 or 308), without loops or avoidable chains. Keep useful legacy URL mappings and document intentional removals.
- [ ] SHOULD: Headers: CSP, HSTS, and sane cache present (hashed assets long-immutable, HTML short/revalidate). NEVER: weaken CSP for a one-off.
- [ ] SHOULD: hreflang if multilingual/multi-regional: reciprocal, valid language-region codes, self-referencing.
- [ ] SHOULD: Structured data valid for currently supported Google features (Rich Results Test), coherent with visible content. FAQ rich results were retired in May 2026. For video pages, verify current VideoObject properties, including creator/author and supported interaction counts, without treating recommendations as required properties.
- [ ] SHOULD: Mobile-first: responsive, no horizontal overflow, tap targets, same content mobile/desktop.
- [ ] SHOULD: Crawl budget: no infinite faceted/param spaces, no soft-404s, prune index bloat.
- [ ] SHOULD: Serve everything over HTTPS and remove mixed content.

## Conditional specializations

Apply only to declared site features or the current migration task. Mark irrelevant blocks N/A and unavailable evidence unmeasured. Extend the existing canonical, sitemap, hreflang and crawl checks. These blocks do not add automated profiles or change CLI scoring. Sources and rationale are in KNOWLEDGE, "Conditional specialization evidence".

### Ecommerce catalogs
- [ ] Inspect crawlable category-to-product links and pagination. Confirm important products remain discoverable without a search form or interaction-only loading. Review representative templates and record sample coverage.
- [ ] Document which facets, sort orders and parameter combinations should be discoverable/indexable. Check the resulting links, responses, robots and canonical signals against that decision. Avoid blanket rules that block useful landing pages or assume blocked URLs can expose a noindex directive.
- [ ] For variants, review stable URLs and the chosen single-page or multi-page model against Google's Product/ProductGroup guidance. Check variant identity, selected offer and truthful structured data. Do not collapse distinct variant URLs indiscriminately.
- [ ] Compare visible price, currency and availability with Product/Offer markup and any authorized Merchant Center/feed evidence. Keep feed consistency unmeasured without access. Full variant/feed validation is manual unless a declared engine covers it. The CLI's existing profiles do not establish eligibility.
- [ ] Verify responses, internal links, canonical and sitemap treatment for unavailable and discontinued items against the documented content/business decision. Use genuine replacement relationships. Flag irrelevant bulk redirects.

### International and multilingual delivery
- [ ] Inventory the declared language/region URL sets. Check direct access and crawlable switching links. Inspect automatic IP/language redirects or cookie-only variants that prevent users or crawlers reaching another version.
- [ ] Extend the existing hreflang checks by reconciling equivalent-page clusters, canonical targets and indexability. Distinguish translations from same-language regional duplicates. Do not canonicalize all translations to one language. Review `x-default` only where a fallback is intended, not as a universal requirement.
- [ ] Include relevant locale hosts explicitly in the authorized audit scope. A same-origin crawl cannot establish cross-domain coverage without permitted target evidence. Record unchecked alternates instead of passing the cluster.

### URL migrations
- [ ] Before a move, retain a baseline and inventory priority URLs using available crawl, sitemap, analytics and backlink evidence. Review the old-to-new map, intentional removals and destination equivalence. Record evidence gaps.
- [ ] After the move, verify permanent redirects to relevant destinations, final responses, updated internal links, canonicals, locale annotations and sitemaps. Check that temporary launch noindex/robots restrictions were removed where indexing is intended.
- [ ] Compare fresh crawls with the reviewed URL map and inspect `scope_comparable` before interpreting additions/removals. The map aligns comparison identities. It does not prove redirects work. Verify old URL responses separately within authorized scope.
- [ ] Follow up on priority URLs with available Search Console indexing/performance data and comparable periods. Separate immediate technical checks from later recrawling and search outcomes. Do not promise a fixed recovery date. See the [before/after guide](../../../docs/FOLLOW_UP.md).

## Additional discovery and content-delivery checks

- [ ] For pagination, verify distinct reachable page URLs and crawlable next-page links. Check what Google can discover without clicking or scrolling. Do not canonicalize all pages to page one merely because they are paginated.
- [ ] Compare important mobile and desktop content, metadata, robots directives and structured data. Test interaction-dependent content. A viewport tag alone does not establish mobile readiness.
- [ ] Review sitemap applicability and submission separately from file presence. A sitemap can omit pages without proving they are unindexable. Inspect declared target responses, canonical policy and truthful modification dates. Do not require an exact match with every HTML file.
- [ ] For an article or guide, review applicable Article/BlogPosting properties against current Google recommendations. Keep JSON-LD structure checks separate from feature eligibility and do not require markup on every page.

## Account-level AI eligibility

When AI visibility is in scope, inspect the effective Search generative AI control and inheritance in Search Console through authorized read access. Code and crawl evidence alone cannot establish that setting. Keep missing access unmeasured and do not change account settings from this gate. See KNOWLEDGE section 7.

## Scope and limits
- On-page/intent/meta copy → seo-onpage-checklist. Backlinks/authority → seo-offpage-checklist. AI-citation/GEO → seo-geo-checklist.
- Report the fix. Let the owning implementation agent apply it. Don't edit build config or app code from this gate.

## Project conventions
Read the host project's `AGENTS.md` and declared context for its URL policy, canonical and `og:url` output, sitemap and robots implementation, header configuration and redirects. Check any separate sitemap and indexability rules for consistency. Do not assume file paths or framework conventions.

## Crawl evidence from this kit
For a public HTTPS site, have `seo-audit` present the `100`, `500`, `unlimited` selector, then save the crawl SQLite database and JSON report in `audits/` inside the selected project. Inspect `crawl_complete`, limits and exclusions before drawing site-wide conclusions. Query `pages`, `issues`, `links`, `resources` and `observations` with `npm run audit:query -- query --database <db> --table <table>`. A missing response or API result is unmeasured, not PASS. Compare two databases with `npm run audit:query -- compare --before <old-db> --after <new-db>` and check `scope_comparable` before interpreting URL additions or removals.

## When you need more detail
Start with this checklist. For more detail (crawl≠index≠rank mechanics, indexing states, rendering, CWV field-vs-lab, header/security detail) open the sibling `KNOWLEDGE.md`.

---
Sources: Google Search Essentials <https://developers.google.com/search/docs/essentials> · Core Web Vitals thresholds <https://web.dev/articles/vitals> · Build a sitemap <https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap> · JavaScript SEO <https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics>

Advanced engines: use `--resource-limit` for image/external checks, `--amp-validator` for the official local WASM validator, and `observations` for PDF, structure, render failures and axe results. `npm run test:browser` verifies actual Chromium under inherited kernel network restrictions. Automated accessibility and structured-data profiles do not establish manual WCAG compliance or rich-result eligibility.

## Save deliverables

Save technical audit reports, crawl databases, evidence and comparisons in `audits/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.
