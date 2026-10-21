# Keyword research deliverables

Use this guide to collect keyword data and save complete research records. It works with connected tools and user-provided exports. Providers may not supply every metric, so record what is missing. Save the research inside the selected client project's `keyword-research/`.

## Collect the fullest available record

Establish seed queries, market/location, language, search engine, device, network where applicable, date scope and authorized tools. Discover the actual tool schema. Retrieve all available business fields for the research task from authorized connected sources, including supported optional response fields and pagination. Inspect existing responses and exports before requesting the same data again.

Use additional keyword, intent, trend, SERP or competitor capabilities when relevant and available within the authorized endpoint and spending scope. Maximize useful coverage within those limits. Do not buy new access or run unbounded paid enrichment to fill a column. Record pagination, sampling, row/call/cost caps, unavailable capabilities and failed requests. An unavailable metric does not justify dropping the keyword.

## Files for each run

Create `keyword-research/YYYY-MM-DD-topic/` with a unique suffix for another run:

| File or directory | Contents |
| --- | --- |
| `research.md` | Scope, findings, prioritized clusters, content opportunities, measurement limits and links to exports |
| `keywords.csv` | Complete normalized keyword table, core columns first and additional columns afterward |
| `keywords.json` | The same records with native types, nested fields and explicit nulls |
| `manifest.json` | Sources, retrieval time/timezone, request scope, measurement periods, units/scales, currencies, field mapping, coverage and collection limits |
| `raw/<provider>/` | Provider responses or original exports, with credentials, authorization headers and personal data removed |
| `monthly-volumes.csv` | Monthly series when available, with record identity, year, month and volume |
| `serp-results.json` | Full available SERP items and features when collected |

Keep other nested arrays or large datasets as named JSON/CSV sidecars and link them from the relevant records and manifest. Preserve all available business data rather than truncating it to fit a chat table. NEVER: store tokens, credentials or transport secrets in these files.

## Stable keyword columns

Always include these first columns in this order. A field the source does not supply remains null in JSON and empty in CSV, with a reason in `missing_fields`. Zero is reserved for an actual returned zero.

| Column | Meaning |
| --- | --- |
| `keyword` | Original keyword text |
| `monthly_search_volume` | Source's reported monthly volume or monthly average. Retain its definition and period |
| `search_intent` | Returned intent or explicitly labeled analyst classification. Retain multiple intents when supplied |
| `paid_competition` | Advertiser competition value or category, with source scale |
| `cpc` | Source's cost-per-click value, with currency and metric definition |
| `keyword_difficulty` | Organic difficulty only when separately supplied. NEVER: substitute paid competition |
| `provider` | Origin of the record |
| `location` | Market/location as returned, with code and readable name when available |
| `language` | Language name/code |
| `search_engine` | Engine |
| `device` | Device or explicit unspecified status |
| `network` | Search/advertising network or explicit unspecified status |
| `currency` | Currency of monetary metrics |
| `measurement_period` | Period covered by the metrics |
| `retrieved_at` | ISO timestamp with timezone |
| `record_id` | Stable identity used by sidecars |
| `missing_fields` | Missing metrics and reasons, such as unsupported, no data, denied, failed or budget-limited |

Use explicit typed or companion fields for competition category, numeric index and scale when a source supplies more than one. Preserve native provider intent labels and confidence. Record `search_intent_origin` as provider or analyst and the reasoning for an analyst classification. Analyst judgments are not tool measurements.

## Additional fields: retain everything available

Append all other returned business fields in stable groups. These examples guide organization. Inspect the actual response rather than assuming support:

1. Demand and trends: per-month history, trend changes, seasonality, volume ranges, update dates and source coverage.
2. Paid search: competition index/category, low/high bids, CPC ranges, additional cost/click/impression metrics and currency.
3. Organic opportunity: difficulty, click potential, related/semantic terms, parent topic, query variants and available intent classifications.
4. SERP evidence: result URLs/domains, positions, titles, snippets, result types, features, result counts, observation dates and available ranking-domain metrics.
5. Project interpretation: cluster, primary/secondary role, target page, existing-page match, cannibalization risk, proposed content type, priority rationale and next action. Mark these as analyst fields.
6. Provider extensions: retain every remaining field under its original provider namespace and preserve nested data in JSON or sidecars.

Put new normalized columns after the stable core in the same groups, with consistent names across runs. Keep unknown fields under a provider namespace, such as `provider_fields.<provider>.<original_path>`, with reversible CSV column mappings in the manifest. Do not discard new fields merely because an earlier export lacked them. Record schema changes and retain native values, precision, units and scales. Protect spreadsheet exports from formula execution while keeping the original text in JSON.

## Multiple sources and ordering

Keep separate records when providers, locations, languages, engines, devices, networks or measurement periods differ. Match compatible keywords without losing original spellings. Preserve conflicting measurements with their source. NEVER: silently choose the highest volume, average incompatible metrics or add duplicate monthly estimates. A consolidated view must name its selected source and link alternatives.

Group the readable review by market/language and cluster, then intent. Within comparable groups, order by monthly volume descending, missing values last, then keyword and provider for deterministic ties. Allow a declared user objective to change the review order, recording its rationale. Do not rank records from different currencies or competition scales together without a documented conversion or normalization.

## Proposals and verification

Connect supported opportunities to `proposals/articles/`, `proposals/guides/`, `proposals/landings/` or another appropriate type. Link each proposal to its research run and record IDs. A proposal includes target intent, primary and supporting queries, page purpose, existing-page overlap, available demand/competition data, recommendation and decision status. Unsupported traffic or ranking forecasts remain excluded.

Before delivery, check record counts against collected pages/exports, core-column presence, source/scope metadata, missing-value reasons, duplicate identities, currencies/scales, sidecar references and preservation of all returned business fields. Summarize findings in chat and give the saved paths. Do not deliver only a short table when richer data was collected.

## DataForSEO binding

When the project declares DataForSEO, follow [the MCP connection and query procedure](../seo-mcp-setup/DATAFORSEO.md). Verify endpoint coverage for each requested metric, request the full standard response and inspect active field filtering before collection. Preserve every returned business field through this export contract. Provider intent, volume and difficulty remain source-specific evidence. API calls, retries and pagination must remain inside the authorized scope and spending cap.
