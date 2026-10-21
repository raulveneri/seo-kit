# SEO Kit contributor guide

Use SEO Kit to plan SEO and GEO work, audit a website and check the result of changes. The kit includes workflows, AI agents and audit tools for new and existing websites.

Before working in this checkout, read `.agents/local/repository-notes.md` if it exists. This optional local guidance is excluded from version control and packages. If absent, continue with this guide.

## Workflow

Optimization covers opportunity discovery, proposal comparison, implementation and measured follow-up. Recommendations depend on the website's goals, constraints and evidence. When several viable strategies remain, explain the trade-offs and obtain the user's selection before dependent implementation. With one reasonable path, explain it and proceed within the authorized scope.

## Repository structure

See [.agents/context/architecture.md](.agents/context/architecture.md) for the resource map and assistant integration behavior.

- `.agents/skills/<name>/SKILL.md`: operational workflows, with supporting detail in `KNOWLEDGE.md` where needed.
- `.agents/agents/*.md`: canonical agent definitions with Claude-compatible frontmatter.
- `.agents/adapters/`: generated assistant adapters.
- `.agents/scripts/` and `.agents/tests/`: executable tooling and validation.
- `docs/`: user documentation.

## Contributing

When a user asks to install this repository, use the global installer: `node .agents/scripts/setup.mjs install`. If a checkout is needed, create a temporary checkout outside the selected client project, run the installer there and remove only that temporary checkout after successful installation. The installer owns OS-specific user-data paths, discovery registration and automatic updates. NEVER: choose a destination inside the client's project or manually replace an assistant's entire configuration directory. A model needs a host with local filesystem and terminal access. A chat-only model cannot perform this installation.

When a user asks to uninstall SEO Kit, run `npm run uninstall` from an available checkout or `node "<managed-data-directory>/seo-kit.mjs" uninstall` using the installed launcher. Use the existing managed removal flow. It deletes the managed installation, including releases and logs, while preserving personal configuration and client deliverables. Report conflicts instead of deleting modified resources manually. See `docs/INSTALLATION.md` for discovery and preview commands.

1. Edit canonical sources. Regenerate adapters with `npm run build` after agent changes.
2. Run `npm run validate` before committing. The npm `files` allowlist defines package contents separately from Git ignores. Check `npm pack --dry-run` when changing resource paths.
3. For factual knowledge changes, update `last_reviewed`, the reference ledger and the changelog.
4. Changes to mandatory rules or strategic recommendations require human review.

Project agent guidance lives in `AGENTS.md` and `.agents/`. Read the architecture reference before changing resource paths, setup or adapter generation.

Website credentials, analytics exports, audit datasets and local configuration belong outside the tracked kit. Scripts manage this repository, generated adapters and documented user-level integrations. Website-specific implementation belongs in the consuming project.

The kit does not run automatic knowledge-refresh jobs. The legacy retirement command disables previously installed refresh services.
