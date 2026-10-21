---
name: seo-mcp-setup
description: Guide setup and verification of SEO data connections over MCP, including DataForSEO, Google Business Profile (formerly Google My Business), GA4, Search Console, PageSpeed Insights, CrUX and browser or crawl tools. Use when enabling, diagnosing or documenting these connections in a consuming project.
---

# Connect SEO data

Read the consuming project's `AGENTS.md` and bindings. Establish the assistant, required data, property or origin, read scope, storage destination and paid-call budget. Discover existing connections first. Load [KNOWLEDGE.md](KNOWLEDGE.md) for provider setup.

1. Map requested capabilities to installed servers and actual tool schemas. Record publisher, version, transport and operations. An HTTP API or CLI adapter is not automatically an MCP server. Do not invent packages, endpoints or credentials.
2. Follow the provider's installation method. Use Google's experimental Analytics MCP for GA4. For DataForSEO, follow [DATAFORSEO.md](DATAFORSEO.md) for the official server, client registration, authentication and budgeted verification. For Google Business Profile, GSC, PSI and CrUX, check the selected bridge against the relevant APIs. If none is selected, explain the available API or authorized-export fallback and ask which bridge to trust before installing one. The kit does not bundle a Business Profile server or CLI adapter.
3. Keep authored project setup guidance and launchers under `.agents/`. Activate through supported client registration: `.agents/mcp.json` is not automatically discovered. Keep credentials in a secret store or environment and use references where supported. NEVER: commit tokens, account configuration or analytics exports to this kit.
4. Use minimum read permissions. Do not change account settings or submit indexing requests during verification. Paid data reads and hosted crawl jobs can cost money: agree endpoints and a cap before executing paid calls.
5. Reconnect as required, discover tools and make one small authorized read against the declared property. Distinguish connected, authenticated and usable for this property. An empty report or missing CrUX record does not necessarily mean authentication failed.
6. Record source, request date, data period, device, URL/origin/property, pagination and cost limits. Redact secrets. A successful API fallback does not verify MCP.

For browser or crawling access, reuse declared tools. Check public-target boundaries, robots, rendering needs, request/time/storage limits and artifact destination. Browser inspection is not a complete crawl or an indexing check. Do not enable unrestricted crawling during setup.

Finish with `capability | server or API fallback | authentication | sample read | limits | next action`. Keep missing access and provider errors explicit. Route first-party evidence to `google-data` and performance work to `seo-pagespeed-optimizer`.

For Google Business Profile, verify the declared account and location separately from Cloud project approval. Check profile information, reviews and performance coverage individually. The required `business.manage` OAuth scope permits management operations. It does not enforce read-only access. Use a server or enforced tool policy that restricts the connection to approved reads. Leave writes disabled during setup and verification. Follow the Business Profile procedure in `KNOWLEDGE.md`.

For DataForSEO, read [the provider procedure](DATAFORSEO.md) before setup or queries. Verify each API family separately. Keep generic request access subject to endpoint/body approval and the agreed spending cap. Route keyword exports to `seo-optimization/KEYWORD_RESEARCH.md` and backlink evidence to `seo-offpage-checklist`.

## Check capability coverage

A Search Analytics binding does not establish access to the Generative AI performance report or Search generative AI settings. Inspect the actual tool schema and use an authorized export or read-only observation where needed. Do not invent API methods or request broader permissions to conceal a capability gap. See `KNOWLEDGE.md` for the checked Google references.

## Save deliverables

Save connection verification summaries in `reports/DD/MM/YYYY/` only when a persistent deliverable is needed. NEVER: save credentials or tokens there.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.

Name report folders by creation date, with zero-padded day/month/year directories: `reports/19/10/2026/search-performance/`. Use the project's timezone, or UTC, and record it. Record the data period separately. Give repeated reports on the same day distinct names.

For keyword-research connections, inspect available demand, intent, paid competition, CPC, organic difficulty, history and SERP capabilities without assuming each is supported. Verify how to request full business records and paginate within the agreed budget. Pass capability gaps to the keyword research workflow.
