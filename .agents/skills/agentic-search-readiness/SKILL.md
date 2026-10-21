---
name: agentic-search-readiness
description: Review AI crawler access, structured content, off-domain presence, agent-readable interfaces and AI share-of-voice measurement. Use for AI-search distribution, bot-access decisions and visibility reporting alongside classic SEO and GEO.
allowed-tools: Read, Grep, Glob, Bash, WebFetch, WebSearch
---

# Check agentic search readiness

Check where search agents can find the brand, understand its content and, where relevant, use the site's declared interfaces. Use this alongside GEO, which reviews whether an individual page is ready to be cited.

Keep classic SEO as the foundation. AI Overviews retrieve content from the Search index. If a check here conflicts with `seo-technical-checklist` or `seo-onpage-checklist`, prioritize classic SEO. NEVER: defer an indexing, canonical or Core Web Vitals fix for a task on this list.

Mark each item PASS / FAIL / N-A with file:line (or the config surface) and the fix.

## Blockers (MUST / NEVER)

- [ ] MUST: compare served robots rules, server responses and CDN/firewall controls with the intended Googlebot policy. Test actual access and record the date and URLs. For Google AI Search, inspect the effective Search generative AI control and parent-property inheritance in Search Console when authorized read access exists. Missing access stays unmeasured. Do not change the setting. See KNOWLEDGE section 3.2.
- [ ] MUST: structured data matches visible content and the applicable Google feature guide. Do not infer that any particular markup guarantees selection.
- [ ] MUST: inspect important text and links in received and rendered HTML. Report access or rendering gaps.
- [ ] MUST: every visibility observation records the query/prompt, observed surface, date and available location/session settings. Do not generalize one response to every user.

## Off-domain presence (conditional review)

- [ ] Record genuine mentions or links found in authorized evidence, with URLs and dates. Do not fabricate endorsements or assign an assumed citation benefit.
- [ ] Compare identity details with the project's declared business information. Record conflicts instead of resolving them by guesswork.
- [ ] Propose another distribution channel only when observed audience needs and the project's resources support it. Do not require an external publication for every topic.

## Agent-readable content and interfaces (SHOULD)
- [ ] SHOULD: the machine-readable expression of key content exists and is current (feeds, sitemaps,
      JSON-LD). These give agents a current, structured view of the content.
- [ ] SHOULD: an explicit position on exposing a conversational/agent endpoint (natural-language
      query interface over the site's own content). Add an endpoint only for a demonstrated need and an authorized maintenance plan.
- [ ] SHOULD: the page passes the automated agent-navigability checks the project's tooling exposes
      (accessibility tree, layout stability, machine-readable summary).
- [ ] SHOULD: N-A unless the project sells: automated checkout interfaces. Mark
      N-A for content and service sites, do not invent a roadmap for them.

## Measurement (MUST when reporting)
- [ ] MUST: distinguish sampled answer visibility from the impressions available in the Search Console Generative AI performance report. Verify the actual binding or authorized export, preserve dimensions and aggregation, and leave unavailable metrics unmeasured.
- [ ] MUST: when reporting a sampled mention/citation share, define the numerator, denominator, fixed prompt set and tested surface. Keep the dates and settings comparable. This is a sample statistic, not a Google ranking metric.
- [ ] MUST: separate first-party measurable data (the project's own analytics/search-console tools,
      per its contract) from third-party estimates. If the project has no analytics wired, mark the
      item `[not measurable]` and say what would need to exist. NEVER: estimate a figure.
- [ ] SHOULD: track referral traffic from AI engines separately from organic. Use actual referral and conversion data. Do not assume volume or intent.

## Scope and limits

- Apply market-specific requirements only when the project needs them. Do not transfer adoption figures or regulatory assumptions between markets.
- Google does not require `llms.txt` for its AI Search features. Maintain it if served, without assigning it a citation benefit. See KNOWLEDGE section 4.2.
- Do not propose a new channel the project cannot sustain. Start with a channel the project can keep useful and current.

## Use with the other checklists
- `seo-geo-checklist`: page-level citability (answer-first, robots access, entity, freshness). This
  skill starts where that one ends. No duplication: if it is about one page being cited, it is there.
- `seo-technical-checklist` / `seo-onpage-checklist`: the classic base that still decides retrieval.
- `seo-offpage-checklist`: link profile and authority. The off-domain block here is about
  **citation surfaces**, which is a different goal from link equity.

## Project conventions
Take every project fact from host project's `AGENTS.md` and project-owned context: host
and edge config, analytics availability, locales, entity/NAP policy, and whether the project sells
anything. Do not hardcode a domain, route, brand token, or command here.

## When you need more detail
Distribution, access and measurement criteria are detailed in the sibling `KNOWLEDGE.md`.

---
Google technical references are listed in `KNOWLEDGE.md`. Project measurements must carry their source and date.

## Save deliverables

Save crawler/access audit evidence in `audits/` and standalone AI-visibility reports in `reports/DD/MM/YYYY/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.

Name report folders by creation date, with zero-padded day/month/year directories: `reports/19/10/2026/search-performance/`. Use the project's timezone, or UTC, and record it. Record the data period separately. Give repeated reports on the same day distinct names.
