# Project agent resources

Edit agent instructions in `AGENTS.md` and `.agents/`. These are the source files for SEO Kit's workflows and assistant adapters.

| Path | Responsibility |
| --- | --- |
| `AGENTS.md` | Repository scope, commands and change contract |
| `README.md` | Repository overview and quick start |
| `docs/` | Usage reference, audit workflow, capabilities and discoverability documentation |
| `.agents/context/` | Architecture and project context loaded when needed |
| `.agents/skills/<name>/SKILL.md` | Reusable operational workflows |
| `.agents/skills/<name>/KNOWLEDGE.md` | Detailed criteria, Google technical references and change history |
| `.agents/agents/*.md` | Canonical agent definitions |
| `.agents/runtime/AGENTS.md` | Portable instructions installed for consuming projects |
| `.agents/adapters/` | Generated assistant adapters. Run `npm run build` |

Scripts and tests live in `.agents/scripts/` and `.agents/tests/`. Service templates live in `.agents/install/`. Upstream repository, update channel and numeric release-approver identity are configured in `.agents/seo-kit.json`. Scheduled jobs check for approved releases at login/startup and daily at local midnight across adapters. Windows uses a GUI script host to start Node without a console. Scheduled invocations disable interactive credential prompts and capture output in managed scheduler logs. `release-policy.mjs` selects a published stable immutable owner-authored GitHub release through `gh`, pinned to a full commit SHA. `main` is a contributor branch, never a candidate fallback. Pinned Python dependency manifests are `.agents/requirements-audit.txt` and `.agents/requirements-audit.lock`. There are no root resource aliases.

The root npm manifest and lockfile remain the public command entry point. Run the documented `npm run` commands from the repository root. Node dependencies remain in the ignored root `node_modules/`. Optional Python/browser runtimes remain in user state outside the repository. Dataset and output guards protect the entire repository, including its root.

`audit_scoring.py` owns versioned applicability and score accounting shared by the build and live auditors. The item-level content contract lives in `.agents/skills/seo-onpage-checklist/CONTENT_REVIEW.md`. `docs/SCORING.md` documents version 2, page/category output and baseline compatibility. This does not change the crawl database schema.

`crawl_privacy.py` provides bounded credential filters and an allowlisted sharing export. The live CLI records HTML-retention policy in each crawl's configuration. Metadata-only runs keep hashes for comparisons and re-fetch missing bodies on resume. `crawl_store.py` owns optional retention and crawl protection using namespaced `meta` entries, without a schema change. `crawl_query.py` exposes `share`, `crawls`, `lock`, `unlock` and preview/apply `retention` commands. Retention preserves unfinished/protected crawls and shared API quota accounting. There is no implicit purge or retroactive anonymization.

`.github/workflows/validate.yml` is repository CI configuration in GitHub's required discovery location, not an agent instruction source. It invokes the canonical npm validation command and checks generated adapter consistency. Executable tooling remains under `.agents/scripts/`.

Global setup is implemented by `.agents/scripts/global-install.mjs`, with OS paths in `platform-paths.mjs`, resource transactions in `integrations.mjs` and user schedulers in `update-services.mjs`. Templates remain under `.agents/install/`. The canonical `.agents/runtime/discovery.md` routing block is merged into user-level instructions. `.agents/runtime/AGENTS.md` contains the full consuming-project workflow.

`npm run setup` installs into `ai-kits/seo-kit` under the user data directory: on Windows, `~/.local/share` avoids packaged-host LocalAppData virtualization. macOS uses Application Support and Linux/Unix uses XDG data paths. `installation()` resolves an explicit `SEO_KIT_MANAGED_BASE` consistently for setup and maintenance, including saved `paths.base`. Existing installations are not moved automatically. This is independent of the source checkout and client projects. Each validated upstream commit is a release under `releases/<commit>/`. `state/installation.json` identifies the active and previous release, assistant paths and resource hashes. `seo-kit.mjs` is the stable entry point. Updates stage a candidate before changing integrations. A recovery journal restores interrupted writes on the next invocation. The previous release is retained during updates. Uninstallation removes the managed installation directory, including all releases, the launcher and logs, while preserving personal assistant configuration and client projects. Do not edit managed releases or installed copies: change canonical source, review and publish it.

Assistant-native configuration paths remain discovery endpoints, not additional authored instruction sources. Setup copies individual skills/agents (Windows requires no symlink privileges) and merges only a marked global instruction block. User content outside it is preserved. Unknown collisions, edited managed files and symlink destinations stop setup/update rather than modifying another kit or checkout. Legacy direct links have an explicit removal command. The installer runs independently of sibling checkouts.

`npm run setup -- --no-services` explicitly opts out of user scheduling. Windows uses a per-user scheduled task. macOS uses launchd. Linux uses user systemd timers or cron. Other Unix systems may use cron. Unsupported schedulers fail explicitly. Optional browser/runtime support is a separate capability and remains subject to its documented isolation requirements.

`.agents/` does not override a host's native discovery. Supported endpoints and checked upstream references are in `docs/INSTALLATION.md`. Profile overrides are resolved at installation and saved for updates. Do not claim skills, hooks, permissions, MCP servers or automatic task selection are active until the actual host confirms loading them. Installation never registers MCP servers or changes permission policy.
