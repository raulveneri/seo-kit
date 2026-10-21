# Interpret checklist scores

`last_reviewed: 2026-10-21` | Scoring version 2

The score describes the kit's measured checklist evidence. It is not a Google score, a probability of ranking, a traffic forecast or proof that every SEO issue was checked. The category budgets remain technical 35, on-page 35, GEO 10, field Core Web Vitals 10 and off-page 10. These are kit policy choices, not empirically calibrated ranking factors.

## Evidence and applicability

Findings use `pass`, `fail`, `unmeasured` and `not_applicable`. A supplied review item needs a concrete explanation even when unmeasured or not applicable. Missing items remain unmeasured. A missing image or JSON-LD block does not earn automatic points. The corresponding structure check is not applicable. Whether the page needs a particular media or structured-data feature remains a separate review task.

On-page content uses the [page review record](../.agents/skills/seo-onpage-checklist/CONTENT_REVIEW.md). Every audited page has its own record and type-specific tasks. Unknown IDs and URLs outside the audited set are rejected. A reviewed sample cannot silently pass other pages.

GEO and off-page evidence use an `items` object instead of one blanket verdict:

| Check | Item IDs |
| --- | --- |
| `geo.review` | `access`, `claims`, `identity`, `measurement` |
| `offpage.review` | `link_evidence`, `link_quality`, `identity` |

Each item contains `status` and `detail`. The parent check retains `source`, ISO `date`, `period` and same-origin `scope`. For `geo.review`, check four areas: effective Googlebot, snippet and generative inclusion evidence, supported visible claims, accurate identity and measurement scope. `offpage.review` requires dated link coverage, reviewed source-page relevance/manipulation and applicable business/review-policy evidence. If identity review is irrelevant, retain a specific reason rather than inventing a local business.

The technical indexing and HTTP evidence groups still accept reviewed `status: pass|fail` plus `detail`. They may also be supplied by the existing live adapters within their documented coverage. Field performance requires a finite, non-negative p75 value and `kind: field_p75`. Lab values cannot substitute for it.

## Calculation

Within each criterion, group findings by audited location. Ignore explicitly non-applicable findings and calculate passing and measured fractions among the remaining items. Each applicable location receives equal influence in that criterion. This prevents one page with hundreds of passing links from overwhelming another page with broken links. A wholly absent criterion remains applicable but unmeasured unless evidence establishes non-applicability.

Multiply these fractions by the criterion's existing weight, then sum:

- `score`: earned weight divided by measured weight, multiplied by 100 and rounded to an integer.
- `coverage`: measured weight divided by applicable weight, multiplied by 100, with two decimal places.
- `score_bounds.lower`: earned weight divided by applicable weight, multiplied by 100.
- `score_bounds.upper`: earned plus unmeasured weight divided by applicable weight, multiplied by 100.

For example, if half the applicable weight was measured and all of it passed, the measured score is 100, coverage is 50%, and the checklist bounds are 50 to 100. These bounds describe how unresolved checks could affect this rubric. They are not statistical confidence intervals or bounds on search performance. Do not report the measured 100 without its coverage and pending checks.

`category_scores` provides the same accounting for each category. `critical_failures` surfaces confirmed failures from the robots, indexing and HTTP groups independently of the numerical average. Review these against the declared site purpose. A high average does not resolve a crawl or indexing failure. `complete` means applicable weighted evidence is complete, and for live reports also requires a complete crawl. It does not mean the site passed or is ready to deploy.

`page_assessments` exposes the page-matched findings and content record for each audited URL. It excludes site-wide and unmatched account evidence, including site-wide off-page review. A page assessment does not establish full-site SEO quality. A single-page crawl also cannot establish incoming links or site-wide uniqueness outside its sample.

## Automatic checks and their limits

- Titles and descriptions are not failed for exceeding 60 or 160 characters. Live length observations remain configurable diagnostics. The Google title/snippet guides set no fixed character limits.
- Multiple H1 elements alone do not fail the main-heading presence check. Semantic nesting and visual prominence still need appropriate review. Follow a host's stricter convention when declared.
- Canonical declarations can point to a preferred alternate URL and can be relative. Missing declarations remain unmeasured. Structural consistency does not establish a correct preferred target or Google's selected canonical.
- Robots rules are evaluated for Googlebot and each supplied indexable page. An absent robots file or sitemap is a review gap, not an automatic violation. Sitemap coverage need not equal every HTML file. Sitemap-index children not inspected by the build auditor remain unmeasured.
- Empty alt text can be correct for decorative images. Attribute presence does not prove semantic accuracy. JSON-LD validity does not prove feature eligibility. The detailed page review remains necessary.

Google references checked 2026-10-21: [title links](https://developers.google.com/search/docs/appearance/title-link), [snippets](https://developers.google.com/search/docs/appearance/snippet), [canonicalization](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [sitemap applicability](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview), [people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) and [Article properties](https://developers.google.com/search/docs/appearance/structured-data/article). The calculation itself is the kit's design.

## Earlier reports and migration

Existing report envelopes remain build schema 1 and live schema 2. `scoring_version: 2` identifies the revised accounting. Old baseline files remain readable, but numerical score deltas are suppressed across scoring versions, different page sets, different scopes or different measured/applicable item sets. A changed sample or newly available evidence is not automatically an optimization improvement. Page types and their required items are part of this comparison.

Old blanket qualitative verdicts remain accepted as input but earn no item-level review credit. Migrate content reviews to `pages` with explicit `page_type` and `items`, and GEO/off-page reviews to `items`. Keep earlier reports. Create a fresh baseline rather than rewriting historical results. NEVER: copy an old summary verdict into every new item without reviewing the evidence.

## Changelog

- 2026-10-21: Introduced scoring version 2, partial and non-applicable evidence, granular page reviews, category/page assessments, checklist bounds and stricter comparison compatibility. Preserved category budgets. No ranking calibration is claimed.
