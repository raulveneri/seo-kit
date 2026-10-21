---
domain: Links and local business evidence
last_reviewed: 2026-10-21
---

# Off-page SEO reference

Use `SKILL.md` for the checklist. Keep website and account changes outside this read-only review.

## 1. Link evidence

Record the source, collection date, scope and sampling limits of each export. Review source pages, destinations, anchor text and relevance. An authorized Search Console Links report export is also a sample, not a complete index. A provider's metric is not a Google measurement. Do not infer a complete link profile from a capped sample.

Google uses links to discover pages and understand relevance. Its link guidance supports descriptive, contextual links. It does not prescribe a healthy anchor-text percentage or a referring-domain growth rate.

## 2. Link spam

Review evidence of links created to manipulate rankings, including paid links that pass ranking credit, excessive exchanges and automated link creation. Do not infer a violation from a low provider score alone.

Use `rel="sponsored"` for paid placements and `rel="ugc"` for user-generated links where applicable. Google also accepts `nofollow` for paid links. These attributes do not authorize deceptive practices.

## 3. Disavow review

Google says most sites do not need the disavow tool. Consider it only when there is both a considerable quantity of spammy, artificial or low-quality inbound links and a manual action, or a likely manual action, caused by them. Try to remove the links first. Escalate the evidence for review. Do not submit a disavow file from this workflow.

## 4. Mentions

Record genuine mentions as observations. A mention without a link is not a backlink. Do not attach a ranking value or an expected conversion rate to outreach. A comparison with another site's links needs comparable source coverage and relevant source-page evidence.

## 5. Local business information

Compare the business's declared name, address or service area, phone, categories, website and hours with its website and Google Business Profile. Record conflicts and missing access. Do not invent locations or reviews.

Review any proposed review-request flow for selective solicitation. Google's Maps policy prohibits discouraging negative reviews, asking only customers expected to leave positive reviews, and offering incentives for reviews. A flow that sends dissatisfied customers only to private support while sending satisfied customers to Google is selective solicitation. Report it for correction. Do not build or operate it from this read-only review. Preserve legitimate support access and genuine customer feedback.

Google describes relevance, distance and prominence as local ranking factors. Its guidance recommends complete, accurate business information and responding to reviews. That does not establish a numerical gain from a particular edit.

## Conditional specialization evidence

Use this section with the checklist's local business review. For multiple locations, check each real operation separately. Record the query, observation location and date for local visibility. Keep review observations distinct from interpretations of customer sentiment. Mark an inapplicable location check N/A.

## 6. Reviewed scoring evidence

The CLI's `offpage.review` group uses three kit-defined items: `link_evidence` (source, date, sample and provider limits), `link_quality` (inspected source-page relevance and manipulation risks), and `identity` (applicable business information and genuine review practices). Supply each verdict and concrete supporting detail in `items`, together with the group's source/date/period/scope. Unknown exports are unmeasured rather than N/A. An identity check can be N/A with a reason when no relevant business or review surface exists. Provider counts alone do not pass quality review.

## Google technical references

| Reference | URL | Last checked |
| --- | --- | --- |
| Search Console Links report | https://support.google.com/webmasters/answer/9049606 | 2026-10-20 |
| Link best practices | https://developers.google.com/search/docs/crawling-indexing/links-crawlable | 2026-10-20 |
| Link spam | https://developers.google.com/search/docs/essentials/spam-policies#link-spam | 2026-10-20 |
| Qualify outbound links | https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links | 2026-10-20 |
| Disavow links | https://support.google.com/webmasters/answer/2648487 | 2026-10-20 |
| Local ranking | https://support.google.com/business/answer/7091 | 2026-10-20 |

Additional references checked 2026-10-21:

| Reference | URL | Scope |
| --- | --- | --- |
| Maps prohibited and restricted content | https://support.google.com/contributionpolicy/answer/7400114 | Fake engagement, rating manipulation and selective review solicitation |
| Local ranking | https://support.google.com/business/answer/7091 | Relevance, distance, prominence and accurate business details |

## Changelog

- 2026-10-21: Added item-level scored review criteria with explicit evidence and applicability limits.

- 2026-10-21: Added review-request policy checks and preserved read-only account boundaries.

- 2026-10-20: Clarified evidence requirements, scope and the checks described above.
