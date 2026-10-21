---
domain: SEO data connection setup
last_reviewed: 2026-10-21
---

# Provider setup reference

Use this reference to choose and verify a data connection. Install the selected server and authorize the account through the provider's own setup flow.

| Capability | Setup and verification |
| --- | --- |
| DataForSEO | Follow [the provider connection procedure](DATAFORSEO.md) for official HTTP/OAuth and pinned local stdio registration, capability discovery, controlled queries, full-field exports and cost/error verification. No bundled server or audit CLI adapter. |
| GA4 | Google's experimental [Analytics MCP](https://github.com/googleanalytics/google-analytics-mcp) uses the Analytics Admin and Data APIs. Enable both, configure Application Default Credentials with Analytics read access, and check property permissions. Verify property discovery and a small dated report. |
| Google Business Profile (formerly Google My Business) | Choose and review a bridge against Google's [prerequisites](https://developers.google.com/my-business/content/prereqs) and [OAuth setup](https://developers.google.com/my-business/content/basic-setup). Confirm approved API access, the authorized account/location and the actual read tools. Profile information, reviews and performance use separate API surfaces. Verify each requested capability below. |
| GSC | Enable Search Console API and authorize the property with `https://www.googleapis.com/auth/webmasters.readonly`. Verify that the selected bridge exposes Search Analytics or URL Inspection. Test accessible properties first. Follow Google's [quickstart](https://developers.google.com/webmaster-tools/v1/quickstart/quickstart-python). |
| PageSpeed Insights | Check the selected bridge's `runPagespeed` coverage, strategy and categories. Configure a restricted key for automated use and test a declared public URL. Follow the [PSI guide](https://developers.google.com/speed/docs/insights/v5/get-started). |
| CrUX | Enable the API and supply an authorized key to the selected bridge. Query the URL or origin for the intended device profile. Keep collection dates and record missing data. Follow the [CrUX API guide](https://developer.chrome.com/docs/crux/api). |
| Browser inspection | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) supports browser inspection and performance diagnostics. Review browser/session requirements and data exposure. Use an isolated project-approved session. |
| Other crawl or backlink tools | Inventory the existing server and verify publisher, tool schema, limits and provenance. The kit's bounded crawl CLI and Moz adapter are API/CLI integrations, not bundled MCP servers. Reuse them when suitable. |

## Verify report coverage separately

### Google Business Profile

Use this connection for the client's own authorized business locations. Declare the Cloud project, account resource, location resource, requested fields, data period and request/page budget in the consuming project's bindings. Keep credentials outside the kit.

1. Complete Google's access prerequisites and project approval, enable the APIs used by the selected bridge and configure its OAuth client. Signing in alone does not establish approved API access or access to a particular location.
2. Review the server's publisher, pinned version, transport, token storage and refresh behavior before registration. Use the provider's local authorization flow. The documented scope is `https://www.googleapis.com/auth/business.manage`. It permits management operations, so restrict exposed tools through the server or an enforced client policy to approved reads. A descriptive read-only label is insufficient. Do not expose unrestricted request tools as a substitute.
3. Discover accounts through Account Management `accounts.list`, then confirm the declared account and location through Business Information `accounts.locations.list`. The latter requires a `readMask`. Request only the fields needed. Keep pagination within the agreed budget. An accessible personal account alone does not verify the target location.
4. Verify reviews only when requested. The Google My Business v4 `accounts.locations.reviews.list` method requires a verified location. A page of reviews is a sample. Preserve returned totals and pagination coverage without publishing reviewer names or raw personal data.
5. Verify performance separately through Business Profile Performance `locations.fetchMultiDailyMetricsTimeSeries`, using one declared location, explicit dates and selected metrics. Preserve the returned metric names and date coverage. Website clicks and call clicks do not establish website sessions, completed calls or conversions.
6. Record connected, authenticated and usable status for each requested capability. Missing reviews or performance access stays unmeasured even when profile discovery succeeds. If no trusted bridge is selected, use an authorized export or a separately authorized API integration and label the result API/export-only. The kit's existing CLI does not collect Business Profile data.

Keep profile edits, posts, review replies, verification actions and user/access changes outside connection verification. Route local identity findings to `seo-offpage-checklist` and first-party metrics to `google-data`.

### Search Console

Search Analytics access does not by itself establish access to the Search Console Generative AI performance report or its inclusion setting. Inspect the bridge's actual schema. Request a dated authorized report export or a read-only settings observation when it does not expose the needed surface. Do not invent an API method or extend account permissions just to fill a report gap. Keep unavailable metrics unmeasured.

## Client registration

Start with the installed client help and supported MCP registration mechanism. User scope avoids adding another authored root configuration. Project scope normally uses the client's native path. `.agents/` does not change discovery.

Google documents this Claude stdio registration:

```bash
claude mcp add analytics-mcp --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/credentials.json" \
  -e "GOOGLE_PROJECT_ID=your-cloud-project" \
  -- pipx run analytics-mcp
claude mcp list
```

Replace placeholders locally after checking provider instructions. Keep credentials outside Git. Authenticate through the provider flow, never by pasting a token into chat. For Codex and OpenCode, use installed MCP help and map the transport and environment fields to the client's supported registration mechanism.

For GSC, PSI or CrUX without a chosen bridge, the existing [CLI API adapters](../../../docs/USAGE.md) collect evidence without MCP. A successful fallback must be labeled API-only. Keep PSI lab results separate from CrUX field records. Google's PSI guide recommends dedicated CrUX APIs for field data.

## Provider integration references

The [DataForSEO connection reference](DATAFORSEO.md#provider-integration-references) records provider-owned dependency documentation, reviewed source and the 2026-10-21 check date. It does not establish Google SEO guidance.

## Google technical references

These Google-published API and integration references were checked on 2026-10-20. Choose and verify a bridge for GSC, PSI or CrUX before installing it. The kit does not list a combined Google server for those three APIs.

Additional references checked 2026-10-21:

- [Generative AI performance report](https://support.google.com/webmasters/answer/16984139): impression report and export coverage.
- [Search generative AI control](https://support.google.com/webmasters/answer/16908024): effective inclusion and inheritance.
- [Business Profile prerequisites](https://developers.google.com/my-business/content/prereqs) and [basic setup](https://developers.google.com/my-business/content/basic-setup): project approval, API enablement and OAuth configuration.
- [Account discovery](https://developers.google.com/my-business/reference/accountmanagement/rest/v1/accounts/list) and [location discovery](https://developers.google.com/my-business/reference/businessinformation/rest/v1/accounts.locations/list): authorization, pagination and required location read mask.
- [Review listing](https://developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list): verified-location requirement, totals and pagination.
- [Daily performance metrics](https://developers.google.com/my-business/reference/performance/rest/v1/locations/fetchMultiDailyMetricsTimeSeries): location, dates, metric selection and authorization.

## Changelog

- 2026-10-21: Added the DataForSEO provider guide and capability-specific routing for MCP setup and authorized queries.

- 2026-10-21: Added Google Business Profile connection setup, capability-specific verification, management-scope restrictions and explicit API/export fallback limits.

- 2026-10-21: Added capability checks for generative reports and inclusion settings without inventing API coverage.

- 2026-10-20: Clarified connection scope and the distinction between MCP and API adapters.
