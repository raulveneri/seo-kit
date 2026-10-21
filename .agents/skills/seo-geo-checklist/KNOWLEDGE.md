---
domain: Google Search AI features
last_reviewed: 2026-10-21
---

# GEO and AI-search reference

Use `SKILL.md` to review a page. Keep eligibility, observed visibility and business results separate.

## 1. Google Search eligibility

For a supporting link in AI Overviews or AI Mode, a page must be indexed and eligible for a Search snippet. Also check the effective Search generative AI control in Search Console, including inherited settings. The current guide requires inclusion in these features. Do not rely only on the older AI-features page when assessing eligibility. Missing account access leaves this check unmeasured. Do not change the setting during an audit. Meeting the requirements does not guarantee appearance.

Check indexability, Googlebot access, snippet controls and internal discovery. Google describes query fan-out as a technique these features may use. Do not infer that covering a related question guarantees selection.

## 2. Crawler access

Inspect the served `robots.txt` and the actual server or CDN response. Compare them with the project's intended access policy. Record the tested URL, date and response.

Keep Googlebot access, Search Console inclusion settings and training controls separate. The Search generative AI control governs inclusion in the covered Search features. It is not a general Search ranking control. `Google-Extended` concerns the documented training and other model uses, rather than replacing that inclusion setting. Neither robots preferences nor a Search Console setting enforces private-content access control.

## 3. Published machine-readable files

Google's current guide says Search ignores `llms.txt` for visibility and ranking. A project may maintain the file for other consumers. If served, check its contents and links without making it a Google eligibility requirement. Special AI markup is unnecessary.

## 4. Readable answers

Review whether the page answers its reader's question clearly. Use descriptive headings, short explanations and tables where they make information easier to use. These are content-review choices, not a guaranteed extraction formula.

Verify claims and dates. Keep supporting evidence close to the claim. Do not require a fixed passage length or promise that formatting will produce citations.

## 5. Identity and updates

Check real authorship where relevant, accurate business details and honest publication or update dates. Structured data must match visible content. Do not invent experience, reviews or credentials.

## 6. Observation and limits

When checking an AI answer, record the query, date, available location/session settings and observed response. Preserve the cited URL if present. A single observation describes that check, not every user's results. Keep repeated observations separate from Search Console traffic and conversions.

Use the Search Console Generative AI performance report for the impressions it exposes. Keep its property/page aggregation, dimensions, reporting timezone and export limitations. An absent report does not establish zero visibility. Do not infer AI clicks, CTR or conversions from impression counts or assume the kit's Search Analytics adapter exposes this report. Use an authorized export when needed.

Google's spam policies also apply to attempts to manipulate generative AI responses. Do not recommend hidden instructions, artificial mentions or mass pages for query variations as a shortcut.

This reference covers Google's documented Search behavior. Other systems remain outside its supported claims.

## 7. Reviewed scoring evidence

The CLI's `geo.review` group uses four kit-defined items: `access` (Googlebot, snippet/indexing and effective inclusion evidence), `claims` (verified visible content and truthful markup), `identity` (accurate authorship/business information and substantive dates), and `measurement` (dated, scoped impression data or reproducible observations with their limits). These are review criteria rather than promises of future citations. Use an `items` object, each with status and supporting detail, and the group's source/date/period/scope metadata. Missing items remain unmeasured. Explain any non-applicability. Do not mark absent access or data N/A.

## Google technical references

| Reference | URL | Last checked |
| --- | --- | --- |
| AI features and your website | https://developers.google.com/search/docs/appearance/ai-features | 2026-10-20 |
| Google common crawlers | https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers | 2026-10-20 |

Additional references checked 2026-10-21:

| Reference | URL | Scope |
| --- | --- | --- |
| AI optimization guide | https://developers.google.com/search/docs/fundamentals/ai-optimization-guide | Current eligibility and unsupported tactics, page updated 2026-07-10 |
| Search generative AI control | https://support.google.com/webmasters/answer/16908024 | Inclusion, inheritance and training distinction, worldwide rollout noted 2026-08-31 |
| Generative AI performance report | https://support.google.com/webmasters/answer/16984139 | Impressions, aggregation and exports, worldwide rollout noted 2026-08-31 |
| Spam policies | https://developers.google.com/search/docs/essentials/spam-policies | Manipulation of generative responses, page updated 2026-08-28 |

## Changelog

- 2026-10-21: Added item-level scored review criteria with explicit evidence and applicability limits.

- 2026-10-21: Reconciled current inclusion controls, generative impression reporting and spam boundaries. Retained earlier reference dates for pages not rechecked.

- 2026-10-20: Clarified evidence requirements, scope and the checks described above.
