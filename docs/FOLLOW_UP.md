# Check SEO changes before and after

Capture a crawl before the change, then compare it with a fresh crawl afterward. Use this for a release, a focused fix or a URL migration.

Run commands from the kit checkout. Replace the example URL and paths with your project's declared values. The assistant creates `audits/` inside the selected project. If you run the CLI yourself, create it before running the commands. Prepare the optional runtime with [the first task guide](GETTING_STARTED.md#add-crawling-or-account-data-when-needed).

## Ask the assistant

Before a change, send this in the website project:

> Use seo-audit to capture a baseline for this project's declared public URL. Record scope, configuration, revision and priority pages. Keep the before database and report in `audits/` inside the selected project.

After the authorized change is available at the audited URL:

> Capture a new crawl with the same scope and settings, using a separate after database. Compare it with the baseline and inspect scope_comparable and scope_differences first. Explain new and resolved findings and changes affecting priority URLs. Check remaining issues in the after database. Separate implementation checks from later search impact.

The agent's audit boundary remains read-only. Implementation belongs to the website project's owner.

## Run the comparison directly

Before the change:

```bash
mkdir -p /path/to/project/audits
npm run audit:live -- --url https://example.org/ --crawl-limit 100 --database /path/to/project/audits/before.sqlite --format json --output /path/to/project/audits/before.json
```

After the change:

```bash
mkdir -p /path/to/project/audits
npm run audit:live -- --url https://example.org/ --crawl-limit 100 --database /path/to/project/audits/after.sqlite --format json --output /path/to/project/audits/after.json
npm run audit:query -- compare --before /path/to/project/audits/before.sqlite --after /path/to/project/audits/after.sqlite --format json --output /path/to/project/audits/comparison.json
npm run audit:query -- query --database /path/to/project/audits/after.sqlite --table issues --format json --output /path/to/project/audits/remaining-issues.json
```

Keep the before database intact and use a new database for each snapshot. `--resume` continues a crawl. It does not create an independent after snapshot. Preserve rendering, exclusions, resource permissions and budgets as well as the URL cap.

## Read the result

| Field or observation | Meaning and next action |
| --- | --- |
| `scope_comparable: false` | Read `scope_differences` and resolve or explain scope differences before interpreting site changes. |
| `change: added` or `removed` | A URL entered or left the observed sample. Check scope and intended URL changes before calling it a regression. |
| `change: modified` | Inspect `fields` for changed status, destination, content hashes, metadata, links, architecture or issue sets. A changed hash alone does not establish a problem. |
| `fields.issues.new` / `resolved` | Rule IDs entered or left the open issue set for a matched page. Investigate the underlying evidence. |
| Remaining issues | Query the after database. The comparison omits unchanged pages and is not a complete list of persistent issues. |

`scope_comparable: true` checks recorded crawl conditions. It does not certify identical external data or prove ranking impact. Record actual fixes verified, intentional changes, unresolved issues and unavailable measurements. Use later Search Console or analytics evidence for search outcomes, with source, dates and comparable periods.

## Compare a URL migration

Save a reviewed JSON object mapping old absolute URLs to their new absolute destinations, for example:

```json
{
  "https://example.org/old-guide": "https://example.org/new-guide"
}
```

Then run:

```bash
mkdir -p /path/to/project/audits
npm run audit:query -- compare --before /path/to/project/audits/before.sqlite --after /path/to/project/audits/after.sqlite --url-map /path/to/project/audits/url-map.json --format json --output /path/to/project/audits/migration-comparison.json
```

The mapping aligns pages for comparison. Verify that actual redirects reach the intended destinations separately. Review mapping collisions and intended removals. Cross-origin comparisons need complete mappings for the old crawl's pages to satisfy the origin check. Other configuration differences can still make scope non-comparable. Separate origins require separately authorized crawls.

For compiled HTML without a live crawl, use the [build audit baseline workflow](AUDIT_WORKFLOW.md#5-fix-and-measure-again). Its JSON baseline is a different input from the SQLite databases used here.
