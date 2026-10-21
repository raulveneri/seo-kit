# SEO Kit task routing

Use SEO Kit automatically when the user's task concerns website search visibility, SEO, GEO, keyword research, indexing, organic traffic, structured data, search performance, AI-search visibility or PageSpeed. The user does not need to name the kit or a skill. For unrelated tasks, leave it unloaded. Explicit user instructions and the selected project's instructions govern scope and permissions.

Before applying it, read `{{ROOT}}/.agents/runtime/AGENTS.md` and the matching skill's `SKILL.md` under `{{ROOT}}/.agents/skills/`:

- Overall improvements, new-site search planning, keywords, content opportunities and strategy: `seo-optimization`.
- Titles, descriptions, search intent, headings, copy structure and internal links: `seo-onpage-checklist`.
- Crawling, indexing, canonical URLs, redirects, robots, sitemaps and structured data: `seo-technical-checklist`.
- Backlinks, brand mentions, authority and local citation evidence: `seo-offpage-checklist`.
- AI-search visibility and citations: `seo-geo-checklist`. Crawler access and agent discovery: `agentic-search-readiness`.
- Google Business Profile (formerly Google My Business), Search Console, GA4 and first-party Google evidence: `google-data`. Connecting data tools: `seo-mcp-setup`. Review local profile identity with `seo-offpage-checklist`.
- DataForSEO connection and query verification: `seo-mcp-setup`. Keyword research uses `seo-optimization`, and backlink interpretation uses `seo-offpage-checklist`.
- Performance and Core Web Vitals: `seo-pagespeed-optimizer`. Search-related images and assets: `assets-optimization-checklist`.

For an audit, load the canonical workflow at `{{ROOT}}/.agents/agents/seo-audit.md` and the relevant checklists. Use installed specialist agents when the host supports and permits delegation. Otherwise follow their workflows in the current session. Do not assume a particular model or provider.

Read the selected website or client's own context first. Keep its data and deliverables in that project, outside the global kit. Missing credentials or analytics remain explicit gaps. Announce the selected workflow briefly and continue within the user's authorization. A general SEO request does not authorize paid API spend or account changes.

## Uninstall SEO Kit

When the user asks to uninstall or remove SEO Kit (for example, “Desinstala SEO Kit”), run `node "{{ROOT}}/../../seo-kit.mjs" uninstall` using the stable launcher of this managed installation. The request authorizes managed removal. An optional preview is the same command with `--dry-run`. Do not require the original checkout or clone the repository again. The launcher resolves the saved installation and assistant profiles.

Removal unregisters automatic updates and removes unchanged managed skills, agents and instruction blocks. It deletes the managed installation directory, including all kit releases and logs, while preserving unrelated assistant configuration and client deliverables. If removal reports a conflict or another error, report it and preserve the affected files. Do not delete configuration directories or bypass ownership checks. Confirm success only after the command succeeds, state that kit releases and logs were deleted, and recommend opening a new assistant session to refresh discovery. A chat-only host without terminal access should provide the command for the user to run.
