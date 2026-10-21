# Global installation and automatic updates

`last_reviewed: 2026-10-21`

SEO Kit is installed once per OS user, independently of any website/client project or model provider. Claude Code, Codex and OpenCode receive native discovery resources from that installation. No plugin marketplace, administrator account or Windows symlink privilege is needed by the installer. Managed enterprise policies can still restrict installation or scheduling.

## Install from any local assistant

Ask a host with terminal and filesystem access:

> Install https://github.com/raulveneri/seo-kit globally for my user, outside the current project, with automatic updates. Follow its installation instructions and preserve my assistant configuration.

The installing assistant reads `AGENTS.md`, selects a temporary directory outside the client project using the OS temporary-directory API, clones the repository there, then runs:

```bash
npm run setup:dry-run
npm run setup
npm run doctor
npm run setup:status
```

Run these commands from the temporary clone. Git, GitHub CLI (`gh`) and Node.js 22 or newer are required. No `npm install` or Python installation is needed for basic setup. Authenticate `gh` and Git with the repository access required for installation. Setup installs only a published owner-approved release, not `main` or uncommitted contributor edits. Delete only the temporary bootstrap clone after success. The stable global installation remains.

A dry run reports paths and scheduling intent without filesystem writes, adapter generation, Git commands or network access. A real install checks for collisions before modifying assistant resources. Rerunning setup is safe for unchanged managed resources. A failure identifies the conflicting file or unavailable scheduler. Do not report success when scheduling failed.

## Data and discovery paths

| OS | Managed data directory |
| --- | --- |
| Windows | `%USERPROFILE%\.local\share\ai-kits\seo-kit` |
| macOS | `~/Library/Application Support/ai-kits/seo-kit` |
| Linux / other Unix | `$XDG_DATA_HOME/ai-kits/seo-kit` (default: `~/.local/share/ai-kits/seo-kit`) |

Only absolute environment overrides are accepted. Data paths are resolved by the installer, never relative to the current project. Windows uses `.local\share` under the current user profile, independently of `LOCALAPPDATA`. macOS uses its native data location. XDG data overrides apply only to Linux/Unix. This avoids packaged Codex Desktop redirecting Windows LocalAppData writes into a private package cache, where terminal checks can pass while Explorer cannot see the reported path. No package identifier or user name is hardcoded.

The resolved base is recorded in `state/installation.json` alongside the assistant paths. Routing instructions and the scheduled task reference that same installation. The stable launcher supplies `SEO_KIT_MANAGED_BASE` for maintenance, so updates, rollback and uninstall use its own directory even when the shell environment differs. An explicit base must be absolute.

Existing installations are not moved or deleted automatically. An installation already under `%USERPROFILE%\.local\share\ai-kits\seo-kit` keeps the same location. For an older LocalAppData installation, use its existing absolute launcher path for status or removal, from the host that can access it. The new default does not discover the old directory. Before reinstalling at the new default, use that managed uninstaller to remove the old integration and scheduler, preserving personal settings and other kits. Do not copy managed state or replace assistant directories manually.

| Host | Skills | Agents | Global routing block |
| --- | --- | --- | --- |
| Codex | `~/.agents/skills/<name>/` | `~/.codex/agents/<name>.toml` | `~/.codex/AGENTS.md`, or existing `AGENTS.override.md` |
| Claude Code | `~/.claude/skills/<name>/` | `~/.claude/agents/<name>.md` | `~/.claude/CLAUDE.md` |
| OpenCode | Shared `~/.agents/skills/<name>/` | `~/.config/opencode/agents/<name>.md` | `~/.config/opencode/AGENTS.md` |

Here `~` means the current user's home on each OS, including Windows. `CODEX_HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME` select the applicable assistant profiles. `OPENCODE_CONFIG_DIR` can select an additional agent-resource directory. OpenCode global instructions remain in its global configuration directory. Install with the same environment used to launch that host. The selected paths are saved so scheduled updates do not depend on interactive shell environment variables. To use a different profile later, remove the old integration and install with the new profile environment.

Setup copies individual resources and records their hashes. It does not replace entire assistant directories, modify providers, enable paid tools, register MCP servers or relax permissions. Unknown same-name resources and locally edited managed files cause a conflict. Symlinked destinations fail explicitly so setup cannot write through an old link into a different repository. Other user configuration and other kits' resources remain in place.

## Automatic updates and recovery

All supported scheduler adapters run automatic updates without opening terminal windows. Linux uses a systemd background service or cron. macOS uses a launchd background job. Windows uses a windowless script host. Scheduled runs have no interactive standard input and write diagnostics to managed logs. Systemd also captures launcher errors in the user journal.

| OS / environment | Per-user scheduling |
| --- | --- |
| Windows | Task Scheduler task `SEO Kit Update-<user SID>`, at user logon and daily at local midnight, using a windowless script host |
| macOS | `com.seo-kit.sync` launch agent, at load and daily at local midnight |
| Linux with a running systemd user manager | `seo-kit-sync.timer`, shortly after user-manager startup and daily at local midnight |
| Linux without a usable user manager, FreeBSD, OpenBSD, NetBSD, Solaris, AIX | User crontab, daily at local midnight and at reboot, when cron supports it |

Updates run in the background while the computer and the applicable user session/scheduler are available. Midnight means 00:00 in the scheduler's local time zone, not UTC. With cron, this is the cron daemon's time zone. Windows and macOS start the per-user job at login. A Linux user timer starts with the user manager, which needs an existing linger configuration to run before login on an unattended server. The installer does not enable linger or install a system-wide service. Windows tasks use an interactive user token and limited privileges. No passwords are stored. Windows uses Windows Script Host (`wscript.exe` with its JScript engine) to launch Node without a console. The updater hides child consoles and scheduled runs disable interactive Git credential prompts. Errors are recorded in `state/updates.log` and `state/scheduler.error.log`. If Windows Script Host is unavailable or blocked by policy, automatic execution needs host-level diagnosis. Setup fails explicitly when the host executable is missing. They are not a promise of updates while the device is powered off, asleep or logged out. Offline failures retry on later scheduled runs. A missing scheduler or policy denial makes setup fail explicitly after resource installation, with a diagnostic. Install/enable the OS scheduler and rerun setup. `--no-services` explicitly opts out. Unknown OS scheduler adapters fail instead of claiming automatic updates are enabled.

The updater checks up to 100 GitHub releases through `gh api` and selects the latest published stable release authored by the numeric owner ID in `.agents/seo-kit.json`. It requires an immutable release, a `vMAJOR.MINOR.PATCH` tag and a full SHA in `target_commitish`. The fetched tag must resolve to that exact SHA. Drafts, prereleases, releases by other accounts and ordinary Git tags are not approvals. API/authentication errors and missing approvals fail closed, with no fallback to `main`. It requires forward history and an unchanged origin/managed checkout, and stages a separate candidate. It rebuilds adapters, runs the Node-based repository doctor and rejects generated/working-tree differences before activation. These installation checks do not replace the full contributor/CI test suite. Changes are updates from the trusted upstream repository, not automatic internet research or knowledge rewriting.

### Owner-approved releases

Publishing a stable immutable release from the configured owner's account is the approval action. Title and release-note text are not authorization. Use a full reviewed commit SHA as the target, and complete contributor validation before publication. The SHA is checked against the tag before any candidate script executes. Approval metadata is saved with the installation. An older approval or a changed record for the installed release is rejected. The first approved release must exist before setup can succeed.

Enable release immutability in repository settings before publishing. Prepare a draft from the owner's account, with a version tag and the reviewed full SHA. Review it, then publish the draft manually from that same account. Creating the draft or pushing a commit alone never approves an update. The installer does not create or publish releases or change repository visibility. Release retrieval requires the corresponding repository access.

The approval checks are implemented in [release-policy.mjs](../.agents/scripts/release-policy.mjs) and exercised by [release-policy.test.mjs](../.agents/tests/release-policy.test.mjs). The record relies on control of the configured owner account. It does not independently verify human presence or release attestations.

To apply the new schedule and windowless launcher to an existing installation, rerun setup from the reviewed release after it is published. This replaces the kit-owned scheduler using the same task name or managed markers and preserves unrelated jobs. Editing this checkout alone does not change a registered task. `npm run sync:watch`, when used manually, also checks once on start and then at local midnight.

Older installed versions that track `main` need an explicit migration using this updated installer after the first approved release is available. Merely editing this checkout does not change an older managed launcher or its scheduler. Keep such installations' legacy update jobs disabled until migration. This installer does not edit managed source in place.

Integration writes use a recovery journal. On a write failure, the previous files and installation state are restored. After process interruption, recovery runs before the next installation/update operation. The active and previous releases are retained. Older clean managed releases are removed. Modified releases are preserved. Local integration edits stop unattended updates rather than being overwritten. The file transaction does not guarantee that all resources switch simultaneously during a running assistant session. Reopen the host after an update if it still uses old instructions.

Under the managed data directory:

```text
seo-kit.mjs                 stable Node entry point
releases/<commit>/          managed repository versions
state/installation.json     active/previous version, paths and resource hashes
state/updates.log           update outcomes, rotated at 1 MiB
state/transaction.json      exists only during integration writes/recovery
```

From an available kit checkout, use:

```bash
npm run setup:status
npm run sync
npm run setup:rollback
npm run uninstall
```

After removing the temporary checkout, invoke the stable entry point with Node and its absolute OS-specific path:

```text
node "<managed-data-directory>/seo-kit.mjs" status
node "<managed-data-directory>/seo-kit.mjs" sync
node "<managed-data-directory>/seo-kit.mjs" rollback
node "<managed-data-directory>/seo-kit.mjs" uninstall
```

Rollback restores the previous validated release and disables automatic updates so they do not immediately undo the rollback. Rerun setup to resume updates. Removal unregisters managed scheduling and removes only unchanged kit resources and the marked instruction blocks. It deletes the managed installation directory, including releases and logs, while preserving unrelated configuration and user text outside those blocks. A modified kit resource must be reconciled before removal. Setup never silently discards it.

## Uninstall

Ask the installed assistant: “Desinstala SEO Kit de mi usuario y desactiva sus actualizaciones automáticas.” Its global routing guidance points to the installed launcher. The original checkout is unnecessary. A host with local terminal access can perform removal directly.

From a checkout:

```bash
npm run uninstall:dry-run
npm run uninstall
```

Without a checkout, resolve the managed data directory using the OS path table above and run:

```text
node "<managed-data-directory>/seo-kit.mjs" uninstall --dry-run
node "<managed-data-directory>/seo-kit.mjs" uninstall
```

The preview describes the removal scope without changing files or services. It does not validate resource conflicts. The actual command checks ownership and refuses modified managed resources. It also checks every retained release for changed, untracked and ignored files before changing integrations or disabling updates. Incomplete staging directories stop removal too. Preserve personal additions outside the installation and resolve reported conflicts before retrying. Ignored runtime caches may also need removal after checking their contents. Do not delete assistant configuration directories. `npm run setup:remove` and the launcher action `remove` remain compatible, including `--legacy` for old direct-link installations.

Successful removal disables managed automatic updates and removes unchanged integrations and marked global instruction blocks. The managed data directory, all installed kit releases, the launcher and logs are deleted. Personal assistant settings and client deliverables stay in place. Open a new assistant session afterward to refresh loaded resources. Unrecognized files in the managed directory stop removal before integrations are changed. Resolve their ownership or move personal files out before retrying.

`setup:status` reports installation integrity, configured scheduler and logs. It does not prove a scheduler has executed: inspect the update log and the native task/timer/job status. Keep the installed Node and Git executables available. If their installation paths change, rerun setup to refresh scheduler definitions.

## Automatic task selection

The user can ask naturally:

- “Improve the organic search visibility of this website.”
- “Why are these pages not getting indexed?”
- “Review the titles and internal links.”
- “Improve this page's Core Web Vitals.”
- “How can this business appear in AI-generated answers?”

Native skill descriptions advertise matching tasks. A small managed global routing block directs the assistant to load the full runtime and relevant workflows, even when the user does not name the kit. The same canonical routing source is used for all supported hosts. Agent definitions inherit the session's model instead of pinning a provider or model name. Claude adapters begin with YAML frontmatter so the host can parse their name, description and skill requirements. Hosts without specialist delegation can follow the canonical agent workflow in the current session.

Verify from a fresh session in the actual website/client project using an ordinary task request. The assistant should announce its matching workflow and read that project's own context. Test an unrelated request too: it should not activate SEO Kit. Higher-priority instructions, disabled skills, host policies, unsupported client versions and model selection behavior can prevent automatic use. A passing file check is not evidence that a model invoked a skill. If unavailable, provide the active release's absolute skill path as a manual fallback and report the discovery gap. Installation cannot add local skills to an arbitrary web chat or an application without a discovery mechanism.

## Migrate an older installation

Old setup linked whole resource directories to the contributor checkout. From that original checkout, first run:

```bash
npm run setup:remove -- --legacy --dry-run
npm run setup:remove -- --legacy
npm run setup
```

The explicit legacy removal recognizes only links pointing to that checkout's known canonical resources and a generated sync service referring to it. It preserves targets and foreign resources. It also retires the old knowledge-refresh jobs. If another toolkit owns a shared registry or symlinked profile, migrate through that toolkit's supported mechanism or use an independent assistant profile. Do not replace its directory. The global installer runs independently of sibling checkouts.

## Validation

`node --test .agents/tests/installation.test.mjs` exercises temporary user profiles and local Git repositories: installation, repeated setup, update, rollback, collisions, local edits, divergent history, network failure, journal recovery, removal, Windows paths independent of LocalAppData, explicit-base maintenance and scheduler generation. It never registers real host jobs. CI declares this suite for Windows, macOS and Ubuntu. Native scheduling/discovery needs a host smoke check on each target. Do not infer those results from mocked scheduler calls. Optional crawler/browser isolation remains governed by the separate audit documentation.

The installer paths and discovery resources are defined in [platform-paths.mjs](../.agents/scripts/platform-paths.mjs) and [integrations.mjs](../.agents/scripts/integrations.mjs). Scheduler generation lives in [update-services.mjs](../.agents/scripts/update-services.mjs). These describe this kit's implementation. Verify discovery and scheduling in the host you use.

Changelog:

- 2026-10-21: Replaced hourly update checks with login/startup and local-midnight scheduling. Added a windowless Windows launcher, hidden child processes, noninteractive scheduled credentials and scheduler logs. Added scheduling and daylight-saving regression coverage. Existing installations apply scheduler changes by rerunning setup from the reviewed published release.

- 2026-10-20: Restricted new installation and update candidates to owner-authored, published stable immutable releases pinned to full commit SHAs. Added bounded GitHub API lookup through `gh`, approval metadata and tests for unapproved branch changes, moved tags and unavailable approval. Repository visibility and publication remain manual decisions.
- 2026-10-20: Added the `uninstall` command, preview shortcut and installed natural-language removal guidance, reusing ownership-checked managed removal. Uninstallation also deletes the managed directory, installed versions and logs while preserving personal configuration and projects.
- 2026-10-20: Added independent global installation, Windows/macOS/Linux scheduler adapters with Unix cron fallback, staged updates and rollback, per-resource ownership and automatic task-routing guidance. Added OS-matrix installation tests, removed fixed agent models and corrected Claude adapter frontmatter.
