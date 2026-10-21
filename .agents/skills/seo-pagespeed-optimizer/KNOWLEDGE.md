---
domain: Technical SEO performance and accessibility optimization
last_reviewed: 2026-10-21
---

# Evidence boundaries

Record the raw Lighthouse reports, device profile, throttling, tool version and build revision. Scores depend on those conditions and the measured metrics. Keep the requested score as the target and compare repeated runs under the same conditions. See [Lighthouse scoring](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring).

[PageSpeed Insights](https://developers.google.com/speed/docs/insights/v5/get-started) provides Lighthouse measurements and diagnostics. Use the dedicated [CrUX API](https://developer.chrome.com/docs/crux/api) for field records and preserve its collection period. A new lab result does not update the historical field record immediately. The CrUX API aggregates a rolling 28-day period and updates daily on a best-effort basis. Preserve the returned collection dates and URL/origin and device scope. Repeated same-day calls do not establish a post-change field result.

Automated checks cannot determine complete accessibility conformance. Follow automated findings with relevant human evaluation, including keyboard and assistive technology checks.

## Google technical references

- Chrome for Developers, Lighthouse scoring: checked 2026-10-20. Lab scoring and variability.
- Google, PSI API guide: checked 2026-10-20. Measurement and dedicated CrUX API recommendation.
- Chrome for Developers, CrUX API: checked 2026-10-20. Field query model.

Additional reference checked 2026-10-21: [CrUX API](https://developer.chrome.com/docs/crux/api), collection window and daily update behavior (page updated 2026-10-13).

## Changelog

- 2026-10-21: Clarified rolling field-data windows and same-day comparison limits.

- 2026-10-20: Reviewed measurement scope and the referenced Google documentation.
