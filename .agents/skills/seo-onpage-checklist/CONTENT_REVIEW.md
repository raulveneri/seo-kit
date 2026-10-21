---
domain: Page and content review evidence
last_reviewed: 2026-10-21
---

# Review a page against its purpose

Use this record for each audited page, including blogs, guides, reviews, landing pages and products. These are the kit's review criteria, informed by the Google references below. They are not Google's ranking factors or a predictive model. A human judgment remains a reviewed judgment even when recorded as a checklist item.

For every finding, retain the exact page URL, reviewed revision or retrieval date, audience, language, target task, supporting excerpt or locator, status, reasoning and proposed action. Use `pass`, `fail`, `unmeasured` or `not_applicable`. Explain every non-applicable item. Missing data, tools, expertise or access means unmeasured. Do not fabricate a target query or a comparison baseline.

## Common items

| ID | Task | Evidence needed to close it |
| --- | --- | --- |
| `intent` | Identify the reader's task and check that the page serves it. | Declared audience/task, inspected content and dated query evidence when available. Do not force a page type from one mixed result set. |
| `original_value` | Identify the page's useful contribution. | Specific original reporting, experience, analysis, examples, tools or a useful synthesis beyond paraphrasing other results. No word-count, keyword-density or source-count target. |
| `accuracy` | Verify consequential and changing claims. | Opened evidence, valid references, applicable dates and corrected contradictions. Escalate claims needing qualified expertise. |
| `responsibility` | Check who is responsible and whether the expertise fits the claims. | Real author, reviewer or business responsibility where readers expect it. Do not award authority from a bio or a schema node alone. |
| `completion` | Check whether the reader can finish the task. | Essential prerequisites, answers, decision information or next steps. Identify actual gaps without demanding every related keyword. |
| `presentation` | Inspect the main content and mobile experience. | Readable page, useful hierarchy, accessible media, working interactions and no obstruction that defeats the task. Source HTML alone does not verify visual usability. |
| `discovery` | Inspect incoming and outgoing contextual navigation. | Crawlable relevant links and actual targets. A single-page scan cannot establish absence of orphans across the whole site. |
| `metadata` | Compare the page's promises with its actual content. | Descriptive title, clear main heading and accurate description when provided. Character counts are diagnostics, not Google limits. |

`intent`, `original_value` and `completion` apply to every reviewed content page and cannot be excluded from the score as not applicable. The other exclusions require a page-specific reason.

## Conditional page types

Choose the type from the page's actual purpose, not a URL substring. Type-specific items supplement the common ones.

| `page_type` | Additional IDs | Tasks |
| --- | --- | --- |
| `generic` | None | Use when no specialization fits. Do not use it to hide applicable specialized tasks. |
| `blog` | `dates` | Reconcile visible and machine-readable dates where used. Identify a substantive update and its real contribution. Do not require changing a date merely to look fresh. |
| `guide` | `instructions`, `limitations` | Check the sequence, prerequisites, examples and expected outcome. Review exceptions, version constraints and relevant risks. Verify instructions only within authorized, suitable test conditions. |
| `review` | `experience`, `comparison` | Check evidence for claimed hands-on experience and measurements. Explain criteria, alternatives, trade-offs and who each option suits. Identify desk research honestly. NEVER: invent tests, purchases or experience. |
| `landing` | `offer` | Verify the real service or offer, scope, supporting proof and next action. Avoid fictitious locations, guarantees and reviews. |
| `product` | `offer` | Reconcile product identity, selected variant, price, availability and purchasing information with the actual offer. Keep unavailable feed evidence unmeasured. |

For articles using Article or BlogPosting markup, review applicable author, image and publication/update properties against the visible page and the current Google guide. That guide specifies recommended properties, not universally required ones. Structured data validity and feature eligibility are different checks.

## CLI evidence contract

Use the existing `onpage.intent_review` group. Its `pages` object must use absolute URLs present in the audited page set. Each page names its `page_type` and an `items` object keyed by the IDs above. Keep `source`, ISO `date`, `period` and same-origin `scope` on the parent group. Missing pages and items remain unmeasured. A blanket `status: pass` earns no content-review credit under scoring version 2.

```json
{
  "checks": {
    "onpage.intent_review": {
      "source": "review of the deployed guide and retained evidence",
      "date": "2026-10-21",
      "period": "deployed revision inspected 2026-10-21",
      "scope": "https://example.org",
      "pages": {
        "https://example.org/guide/": {
          "page_type": "guide",
          "items": {
            "intent": {
              "status": "pass",
              "detail": "The guide serves the declared setup task. Prerequisites and final verification are identified in the retained review."
            },
            "instructions": {
              "status": "fail",
              "detail": "Step 3 uses a removed option in the declared software version. The retained authorized test reproduces the error."
            }
          }
        }
      }
    }
  }
}
```

This deliberately partial example leaves all other criteria unmeasured. Record the fix and repeat the affected checks. Do not copy the example's verdicts into a real audit. Keep supporting material in the selected project's `audits/` directory.

## Google technical references

| Reference | URL | Checked | Scope |
| --- | --- | --- | --- |
| People-first content | https://developers.google.com/search/docs/fundamentals/creating-helpful-content | 2026-10-21 | Originality, task satisfaction, responsibility and trust |
| SEO Starter Guide | https://developers.google.com/search/docs/fundamentals/seo-starter-guide | 2026-10-21 | Content organization, discovery and SEO limitations |
| High-quality reviews | https://developers.google.com/search/docs/specialty/ecommerce/write-high-quality-reviews | 2026-10-21 | Experience evidence, measurements and decision criteria |
| Article structured data | https://developers.google.com/search/docs/appearance/structured-data/article | 2026-10-21 | Applicable recommended properties and visible information |
| Title links | https://developers.google.com/search/docs/appearance/title-link | 2026-10-21 | Descriptive titles and main-title prominence |
| Snippets | https://developers.google.com/search/docs/appearance/snippet | 2026-10-21 | Page-derived snippets and description limits |
| Crawlable links | https://developers.google.com/search/docs/crawling-indexing/links-crawlable | 2026-10-21 | Discovery and link context |

## Changelog

- 2026-10-21: Added item-level content review, conditional page types and the scoring-version-2 evidence contract.
