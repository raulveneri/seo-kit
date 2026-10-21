---
domain: Crawling, indexing and page experience
last_reviewed: 2026-10-21
---

# Technical SEO reference

Use `SKILL.md` for the checklist. Record what was inspected and keep missing evidence unmeasured.

## 1. Crawlability and indexing

Crawling, indexing and serving results are separate stages. `robots.txt` controls crawling. A blocked URL can still appear in Search. To prevent indexing, use a supported `noindex` directive on a page Google can crawl, or restrict access when the content is private.

Review canonical signals across metadata, redirects, sitemaps and internal links. A canonical is a signal, not a command. Compare the intended destination with Google's selection when Search Console access is available. Investigate a discrepancy before calling it a defect. Do not force self-canonicals on deliberate duplicate alternatives.

After changing duplicate content, allow for recrawling and processing. Google's troubleshooting guidance notes that a duplicate cluster may persist for up to two weeks after a fix. Do not treat that as a universal recovery deadline.

## 2. URL consistency

Use the consuming project's declared URL policy. Link directly to intended destinations. Keep canonicals, redirects and sitemap URLs consistent. Preserve useful old-to-new mappings during a migration, and test actual responses. A map file alone does not prove a redirect works.

## 3. Core Web Vitals

The good thresholds are LCP at most 2.5 seconds, INP at most 200 milliseconds and CLS at most 0.1, evaluated at the 75th percentile. Preserve device segmentation and the collection window returned by the field-data source.

Use lab tools to diagnose resource discovery, main-thread work and layout shifts. They do not replace field measurement. Identify the actual LCP element before changing loading priority. Avoid lazy-loading an LCP image. Reserve image space and test changes under comparable conditions.

## 4. Rendering

Inspect received and rendered HTML. Google can render JavaScript, but rendering has limitations. Server-side rendering or pre-rendering can make content available without waiting for client execution. Check that important text, links and metadata are available to the intended crawler. Do not claim JavaScript content is universally unindexable.

## 5. Sitemaps and robots

Include the canonical URLs intended for Search and accurate modification dates. Keep a sitemap within 50,000 URLs and 50 MB uncompressed, or split it. Review crawl restrictions against the site's intended public and private areas. A sitemap does not guarantee indexing.

## 6. Headers and security

Check HTTPS, cache behavior and the project's security-header requirements. Preserve working access controls. These are implementation checks. Do not treat a particular CSP or HSTS configuration as a separate Google ranking requirement.

## 7. Structured data

Check the current Google feature guide, visible-content agreement and actual test results. Valid JSON-LD does not establish feature eligibility or guarantee a rich result. Review required and recommended properties for each supported type instead of treating every vocabulary property as a Google requirement.

Google retired FAQ rich results in May 2026. Do not classify a site as missing an active Google rich-result feature because it lacks FAQPage markup. For sites with video, check the September 24, 2026 VideoObject guidance for supported `creator`/`author` and `interactionStatistic` properties. Do not turn recommended properties into universal requirements or invent interaction counts.

For Google AI visibility, check the effective Search generative AI control as well as crawlability and snippet eligibility. A code crawl cannot establish an account setting. Route missing account evidence to `google-data` and keep it unmeasured.

## 8. Conditional discovery checks

A sitemap is useful for discovery, especially for larger or less well-linked sites, but not required for every site. Missing files and uninspected sitemap-index children remain review gaps rather than automatic Google violations. A submitted URL set need not equal every HTML file. Googlebot-specific robots groups and individual path rules must be checked. A global wildcard test alone is insufficient.

Inspect pagination through unique page URLs and crawlable sequential links, and review the intended canonical for each page. For mobile indexing, compare actual important content, metadata and directives with the desktop presentation. Viewport metadata cannot establish that equivalence. Apply these tasks only to existing features.

The CLI's canonical check validates supplied declarations without forcing a self-canonical. Absent declarations require review, not a declaration that Google cannot index the page. Supplied relative canonicals can be understood, though Google recommends absolute URLs. The automatic check does not establish Google's chosen canonical.

## Conditional specialization evidence

For ecommerce, inspect category-to-product discovery, facet policies and the chosen single-page or multi-page variant model. Match offers to visible price and availability. Keep feed consistency unmeasured without authorized evidence.

For language and region variants, check accessible URLs, equivalent-page groups and canonical/hreflang consistency. Include each host explicitly in scope. Do not infer complete cross-domain coverage from a same-origin crawl.

For migrations, preserve priority URL evidence, map equivalent destinations, test permanent redirects and update internal signals. Monitor later indexing and performance separately from immediate technical checks.

## Google technical references

| Reference | URL | Last checked |
| --- | --- | --- |
| How Search works | https://developers.google.com/search/docs/fundamentals/how-search-works | 2026-10-20 |
| Canonicalization | https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls | 2026-10-20 |
| Canonical troubleshooting | https://developers.google.com/search/docs/crawling-indexing/canonicalization-troubleshooting | 2026-10-20 |
| Block indexing | https://developers.google.com/search/docs/crawling-indexing/block-indexing | 2026-10-20 |
| Web Vitals | https://web.dev/articles/vitals | 2026-10-20 |
| Core Web Vitals and Search | https://developers.google.com/search/docs/appearance/core-web-vitals | 2026-10-20 |
| Optimize LCP | https://web.dev/articles/optimize-lcp | 2026-10-20 |
| Optimize CLS | https://web.dev/articles/optimize-cls | 2026-10-20 |
| JavaScript SEO | https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics | 2026-10-20 |
| Sitemaps | https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap | 2026-10-20 |
| Structured data | https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data | 2026-10-20 |
| Product variants | https://developers.google.com/search/docs/appearance/structured-data/product-variants | 2026-10-20 |
| Faceted navigation | https://developers.google.com/crawling/docs/faceted-navigation | 2026-10-20 |
| Multilingual sites | https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites | 2026-10-20 |
| Site moves | https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes | 2026-10-20 |

Additional references checked 2026-10-21:

| Reference | URL | Scope |
| --- | --- | --- |
| Documentation updates | https://developers.google.com/search/updates | FAQ retirement and 2026-09-24 VideoObject revision |
| Video structured data | https://developers.google.com/search/docs/appearance/structured-data/video | Current supported video properties, page updated 2026-09-24 |
| Search generative AI control | https://support.google.com/webmasters/answer/16908024 | Inclusion separate from code-level indexability |

Additional discovery references checked 2026-10-21:

- [HTTP status behavior](https://developers.google.com/search/docs/crawling-indexing/http-network-errors), permanent redirects and intentional removals.
- [Robots rules](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec), agent selection and path precedence.

- [Sitemap overview](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview), applicability and discovery limits.
- [Robots introduction](https://developers.google.com/search/docs/crawling-indexing/robots/intro), crawl-control scope.
- [Canonicalization](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), preferred targets and relative declarations.
- [Pagination](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading), sequential discovery and canonical choices.
- [Mobile-first indexing](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing), content and metadata parity.

## Changelog

- 2026-10-21: Added conditional discovery/mobile checks and corrected universal robots, sitemap and self-canonical assumptions in scoring guidance.

- 2026-10-21: Updated feature-lifecycle checks, video guidance and account-level AI eligibility boundaries.

- 2026-10-20: Clarified evidence requirements, scope and the checks described above.
