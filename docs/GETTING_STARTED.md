# Complete the first SEO task

Choose one website or client and one goal. Use a dedicated project folder to keep its context and generated files together.

## Install and check the kit

Requirements: Git, GitHub CLI (`gh`), Node.js 22 or newer and a local Claude Code, Codex or OpenCode host on Windows, macOS or Linux. Installation requires a published owner-approved release. Authenticate `gh` with read access while the repository is private. Basic installation does not require Python. The audit CLI requires Python 3.10 or newer.

Use a temporary kit checkout outside the website/client project:

```bash
git clone https://github.com/raulveneri/seo-kit.git
cd seo-kit
npm run setup:dry-run
npm run setup
npm run doctor
```

For an existing checkout, start at the dry run. Setup creates a separate managed global installation, registers individual resources and enables hourly updates. After successful setup, the temporary checkout can be removed. To opt out of automatic updates, use `npm run setup -- --no-services`. Existing configuration is preserved. Conflicts fail explicitly. See [paths, migration and recovery](INSTALLATION.md).

Expect `doctor: PASS`. A failure names the missing or invalid resource. This verifies repository and installed resource files, not whether an assistant has loaded a skill or an external account is accessible.

## Select the website or client folder

Create or reuse a folder for the website or client and open it as the active project in your assistant. The website's existing source folder works. If you only need research, audits or proposals, a working folder without code or Git is enough.

Keep a separate project folder for each website or client. Select that folder before starting a task or switching clients. The assistant creates `keyword-research/`, `audits/`, `proposals/` and dated `reports/` inside it as needed. This keeps each client's work together as you add more projects.

Keep the SEO Kit checkout separate. Read the selected project's `AGENTS.md` and declared context for the website identity, goals, routes, constraints and available data connections. If that context is missing, provide it before work that depends on it. See the [client folder example](USAGE.md#one-project-folder-per-website-or-client).

## Verify assistant discovery

Open a fresh assistant session in the selected website or client project after setup. In Claude Code, Codex or OpenCode, send:

> Review opportunities to improve this website's organic search visibility. Read its declared context and identify missing evidence. Produce recommendations only for now.

The assistant should select `seo-optimization` from the task intent, announce it and use the website's actual context without you naming the kit. If it cannot find the skill, run `npm run doctor` from the kit checkout and reopen the assistant. Check its skill discovery interface. A passing doctor does not establish that every client integration loads user-level resources.

If discovery remains unavailable, give the assistant the active release's absolute `.agents/skills/seo-optimization/SKILL.md` path shown by `setup:status` and ask it to read that file explicitly. This is a manual fallback, not a claim of native integration. See the [architecture reference](../.agents/context/architecture.md) for resource ownership.

## Request a first plan

Send this in the website's project:

> Use seo-optimization to review this website's declared goals and current implementation. Identify the most useful opportunities, distinguish evidence from assumptions and recommend a plan with effort, risks and verification steps. If several viable strategies remain, present the trade-offs for selection. Produce recommendations only for now.

The proposal should tell you what the assistant found, which pages or templates need work, what it recommends and how to check the result. It should also name any missing data. For a new website, requirements and source files are enough to start. Add historical analytics or a live crawl when useful.

When ready, select a proposed path and request implementation. The workflow should apply authorized changes and run the website project's relevant checks. Search impact needs later measurement. A successful build alone does not prove it.

## Add crawling or account data when needed

For a public-site baseline, ask for `seo-audit`. The optional crawler needs its own runtime preparation:

```bash
npm install
npm run setup:audit
```

Run those commands from the kit checkout. Then follow the [bounded crawl instructions](USAGE.md#crawl-a-public-website), choosing the real website URL and creating `audits/` inside the selected client project. A source review does not require installing the browser runtime.

For GA4, Search Console or other connected evidence, request `seo-mcp-setup`. Start with the source needed for the task and verify access to the declared property. Store reports and exports in the selected project following the output locations below. Keep credentials in the project's authorized credential store.

To review regressions, use the [before/after guide](FOLLOW_UP.md) for assistant requests, separate snapshots, comparison commands and URL migrations. Check scope comparability before interpreting differences.

## Find generated files

The assistant saves keyword research in `keyword-research/`, audit artifacts in `audits/`, proposals grouped by type in `proposals/articles/`, `proposals/guides/` and `proposals/landings/` and standalone reports in `reports/DD/MM/YYYY/` inside the selected client project. It creates directories when needed and returns saved paths. See [output locations](USAGE.md#generated-files-in-the-selected-project).
