# SEO Kit: Website SEO/GEO Optimization

Use SEO Kit to decide what to improve on a website, make the changes and check the result. It includes SEO and GEO workflows, AI agents and audit tools for Claude Code, Codex and OpenCode. You can start with a new website or work on one that is already live.

Start in your assistant's command-line, IDE or app integration. Connect the tools your task needs with the [MCP connection guide](.agents/skills/seo-mcp-setup/SKILL.md). With the right tools and permissions, the assistant can also apply approved changes through your browser.

[First task guide](docs/GETTING_STARTED.md) · [Before/after tracking](docs/FOLLOW_UP.md) · [Usage reference](docs/USAGE.md) · [Audit workflow](docs/AUDIT_WORKFLOW.md) · [CLI capabilities and limitations](docs/CAPABILITIES.md)

The checklists and audit scoring use this kit's own SEO and GEO criteria.

## What you can do

- **Choose where to focus.** Research keywords with connected data sources, find opportunities and compare proposals by benefit, effort and risk. The [optimization workflow](.agents/skills/seo-optimization/SKILL.md) recommends suitable paths. When several make sense, you choose.
- **Check a website.** Audit compiled HTML or crawl a public HTTPS site. Review titles, headings, canonicals, robots directives, sitemaps and links. Use the specialist checklists for search intent, backlinks and AI-search readiness.
- **Use your own data.** Connect Google Business Profile, GA4, Google Search Console, PageSpeed Insights and CrUX, or use authorized exports to ground decisions in the site's results. The connection guide covers provider requirements and bridge selection. Missing data stays visible in the report.
- **Improve page experience.** Use [seo-pagespeed-optimizer](.agents/skills/seo-pagespeed-optimizer/SKILL.md) to make measured fixes across performance, accessibility, Best Practices and SEO, including a target of 100 when requested.
- **Query DataForSEO.** Use the [connection guide](.agents/skills/seo-mcp-setup/DATAFORSEO.md) for official MCP registration, credentials, keyword/SERP/backlink capability checks and authorized query budgets.
- **Check what changed.** Store crawl evidence in SQLite, query findings, export JSON or CSV and compare successive crawls after implementation.

**Note:** Automated checks do not guarantee indexing, rankings, AI citations, rich results or accessibility conformance. The [capability matrix](docs/CAPABILITIES.md) explains what is checked and what still needs review.

Generated files stay in the selected client or website project: keyword research in `keyword-research/`, audits and evidence in `audits/`, proposals grouped in `proposals/articles/`, `proposals/guides/`, `proposals/landings/` and other relevant types, and standalone reports in dated folders such as `reports/19/10/2026/`. The assistant creates folders as needed and preserves earlier runs. See [output locations](docs/USAGE.md#generated-files-in-the-selected-project).

## Quick start

Requirements: Git, GitHub CLI (`gh`), Node.js 22 or newer and a local assistant host such as Claude Code, Codex or OpenCode. Authenticate `gh` with the repository access required for installation. Global installation supports Windows, macOS and Linux. Additional Unix systems can use the cron adapter when available. A chat-only model without filesystem/terminal access cannot install local resources.

Tell your assistant:

> Install https://github.com/raulveneri/seo-kit globally for my user, outside the current project, with automatic updates. Follow the repository's installation instructions and preserve my existing assistant configuration.

The assistant should use a temporary checkout outside your website/client project and run:

```bash
git clone https://github.com/raulveneri/seo-kit.git
cd seo-kit
npm run setup:dry-run
npm run setup
npm run doctor
```

`setup` creates an independent managed installation in the user data directory listed below, registers skills and agents for Claude Code, Codex and OpenCode, and configures hourly checks for owner-approved releases using your user's scheduler. Only published, stable, immutable GitHub releases authored by the configured owner and pinned to a full commit SHA can be installed. Commits on `main`, drafts and ordinary tags do not trigger updates. Without an approved release, installation stops. An existing version is preserved on update failure. See [owner approval](docs/INSTALLATION.md#owner-approved-releases). The temporary checkout can then be deleted. Existing configuration is preserved. Conflicting resources cause an explicit error instead of replacement. No administrator rights or Windows symlink privileges are required by the installer.

| System | Default managed installation |
| --- | --- |
| Windows | `%USERPROFILE%\.local\share\ai-kits\seo-kit` |
| macOS | `~/Library/Application Support/ai-kits/seo-kit` |
| Linux and other Unix | `${XDG_DATA_HOME:-~/.local/share}/ai-kits/seo-kit` |

On Windows, setup uses the user profile instead of `LOCALAPPDATA` to avoid packaged Codex Desktop redirecting the installation into a private cache. The managed path is shared with external tools, including Explorer. Existing installations are not moved automatically.

Open a fresh assistant session in the website's project and ask naturally, for example: “Improve this website's organic search visibility.” Skill descriptions and global task-routing guidance let the assistant select the kit without you naming it. A file check cannot prove a particular model will select it: verify discovery in your actual host.

See [global installation, updates and migration](docs/INSTALLATION.md) for profile overrides, scheduler requirements, recovery and existing installations. The expected file-verification result is `doctor: PASS`. The optional Python audit runtime is separate.

### Uninstall

Tell your assistant:

> Desinstala SEO Kit de mi usuario y desactiva sus actualizaciones automáticas.

The installed guidance directs the assistant to the managed uninstaller, even after the temporary checkout is deleted. From an available checkout, you can also run `npm run uninstall` (`npm run uninstall:dry-run` previews removal). It deletes installed kit versions and logs while preserving your personal assistant configuration and client files. See [uninstallation](docs/INSTALLATION.md#uninstall) for the standalone command and conflict handling.

### Open a folder for each website or client

Create or reuse a dedicated folder for the website or client you want to work on. Open that folder as the active project in Claude Code, Codex or OpenCode before requesting SEO work. You can use the website's existing source folder or an SEO working folder without code or Git.

The assistant uses the selected project to keep research, audits, proposals and reports together. When working with several clients, select the right folder before each task so their files and context stay separate. Keep the SEO Kit checkout separate from client work. See [how to organize client folders](docs/USAGE.md#one-project-folder-per-website-or-client).

### Choose the first task

Open the website's project in Claude Code, Codex or OpenCode and send one of these requests:

| Goal | Request |
| --- | --- |
| Decide what to improve | "Inspect this project's SEO goals and implementation, identify opportunities and recommend a plan before making changes." |
| Review a new website | "Review this site's search requirements, routes and templates before launch. State missing context and provisional assumptions." |
| Audit an existing website | "Audit this project's declared public URL. Explain the crawl scope and evidence gaps before crawling." |
| Check a recent change | "Compare this project's before and after crawl databases. Check scope comparability and report new, resolved and persistent findings." |
| Connect search data | "Identify the search-data connections this task needs and verify a small authorized read from the declared property." |

These are natural-language requests, not new slash commands. The assistant should identify the workflow and project context. If it cannot find a skill, follow the [discovery checks](docs/GETTING_STARTED.md#verify-assistant-discovery).

### Start an optimization task

Use the `seo-optimization` agent or skill in the website's project. For example:

> Optimize this website for its declared SEO goals. Identify opportunities and recommend suitable approaches. If several viable paths exist, explain the trade-offs and let the user choose before implementing dependent changes. If only one reasonable path exists, explain it and proceed within the authorized scope. Verify the results.

The assistant compares useful approaches and explains its recommendation. If several strategies make sense, you choose before implementation. With one reasonable path, it explains why and continues within your authorization. To review proposals first, ask for recommendations only.

For a new site, start with its requirements. For an existing site, use its content and available data. Ask for `seo-audit` when you need to collect and review audit evidence.

### Audit compiled HTML

Run from the kit directory with the paths for your own project:

```bash
mkdir -p /path/to/project/audits
npm run audit -- --site /path/to/project/dist --base-url https://example.org --format json --output /path/to/project/audits/audit.json
```

This mode reads the compiled site without network requests. The report separates score from evidence coverage. Unavailable external measurements remain unmeasured. Follow the [SEO/GEO audit workflow](docs/AUDIT_WORKFLOW.md) to collect evidence and prioritize fixes.

Live crawls keep results local to the selected client project and default to metadata-only SQLite storage. Retain filtered source with `--store-html raw|rendered|both` when needed. Reduced sharing exports, protected crawls and opt-in retention are described in [local crawl privacy](docs/USAGE.md#local-crawl-privacy-sharing-and-retention). Filtering is not general anonymization. Review data before sharing with people or AI services.

### Crawl a public website

Prepare the optional audit engines, then run a bounded crawl:

```bash
mkdir -p /path/to/project/audits
npm install
npm run setup:audit
npm run audit:live -- --url https://example.org/ --crawl-limit 100 --database /path/to/project/audits/crawl.sqlite --format json --output /path/to/project/audits/audit-live.json
```

The assistant creates `audits/` inside the selected project before running the audit. For manual CLI use, create it first as shown above. The crawler respects robots directives, restricts navigation to the same origin and enforces request, time and storage budgets. Optional JavaScript rendering requires Linux and supported browser isolation. See the [live audit reference](docs/USAGE.md#crawl-a-public-website) for prerequisites and limits.

Query issues and compare crawls:

Follow the [before/after guide](docs/FOLLOW_UP.md) to capture separate snapshots, interpret differences and compare URL migrations. It includes assistant requests and commands.

```bash
mkdir -p /path/to/project/audits
npm run audit:query -- query --database /path/to/project/audits/crawl.sqlite --table issues --format json
npm run audit:query -- compare --before /path/to/project/audits/old.sqlite --after /path/to/project/audits/new.sqlite --format json
```

## SEO and GEO skills and agents

Skills provide operational workflows and quality checklists. Supporting `KNOWLEDGE.md` files, where present, hold detailed criteria and Google technical references.

| Skill | Purpose |
| --- | --- |
| [SEO optimization](.agents/skills/seo-optimization/SKILL.md) | Opportunities, compared proposals, critical recommendations, user choice, implementation and follow-up |
| [On-page SEO](.agents/skills/seo-onpage-checklist/SKILL.md) | Search intent, titles, descriptions, headings and internal links |
| [Technical SEO](.agents/skills/seo-technical-checklist/SKILL.md) | Crawlability, indexing, canonicals, sitemaps and performance evidence |
| [Off-page SEO](.agents/skills/seo-offpage-checklist/SKILL.md) | Backlink evidence, referring domains, brand mentions and local consistency |
| [GEO and AI-search visibility](.agents/skills/seo-geo-checklist/SKILL.md) | Content accessibility, attribution and citation readiness |
| [Agentic search readiness](.agents/skills/agentic-search-readiness/SKILL.md) | Discoverability and interpretation by search agents |
| [Search and performance assets](.agents/skills/assets-optimization-checklist/SKILL.md) | Image, font and media checks relevant to search and performance |
| [Google data](.agents/skills/google-data/SKILL.md) | Project-declared first-party Google data and evidence |
| [MCP connection guide](.agents/skills/seo-mcp-setup/SKILL.md) | Set up data access and verify a small read |
| [PageSpeed optimization](.agents/skills/seo-pagespeed-optimizer/SKILL.md) | Measure, fix and recheck performance and accessibility |

The five canonical agents are [seo-optimization](.agents/agents/seo-optimization.md), [seo-audit](.agents/agents/seo-audit.md), [seo-onpage](.agents/agents/seo-onpage.md), [seo-offpage](.agents/agents/seo-offpage.md) and [seo-technical](.agents/agents/seo-technical.md). Claude Code, Codex and OpenCode adapters are generated with `npm run build`.

## Documentation and contributing

- [Usage reference](docs/USAGE.md): installation, CLI options, integrations, scheduling and evidence format.
- [Agent architecture](.agents/context/architecture.md): canonical `.agents/` resources and executable tooling.
- [Audit workflow](docs/AUDIT_WORKFLOW.md): scope, measurements, manual review, prioritization and repeat audits.
- [Capability matrix](docs/CAPABILITIES.md): implemented checks, external-data requirements and limitations.
- [Repository discovery](docs/DISCOVERABILITY.md): GitHub metadata and ways to find the kit.

```bash
npm run build
npm run validate
```

[Repository validation](.github/workflows/validate.yml) runs these checks in GitHub Actions for pushes to `main`, pull requests targeting `main`, and manual runs. It installs locked dependencies and rejects uncommitted generated-adapter changes. See [validation scope](docs/USAGE.md#repository-validation) for optional checks.

Edit canonical skills in `.agents/skills/` and agents in `.agents/agents/`. Run the build to regenerate adapters. Scripts, tests, service templates and audit dependency manifests also live in `.agents/`. Keep website credentials, analytics exports and audit datasets in the consuming project.

Contribution instructions and validation requirements are documented in [AGENTS.md](AGENTS.md).

## License and attribution

Copyright (c) 2026 Raúl Veneri (raulveneri).

SEO Kit uses the [SEO Kit Free Use License 1.0](LICENSE). You may use it for
free, including professional work for paying clients, modify your copy and
share copies or forks free of charge. Preserve [NOTICE](NOTICE), the license
and the original credits. Identify modifications and their authors.

You may charge for services performed with SEO Kit. You may not sell the kit,
sell derivative versions or charge for access to a hosted version of the kit.
Copies supplied with a service must remain free under the same license. Ordinary
client reports and website improvements are not subject to these distribution
conditions unless they reproduce substantial parts of the kit.

This is a source-available license with resale restrictions, not MIT or an
unrestricted open-source license. Read [LICENSE](LICENSE) for the complete terms.
