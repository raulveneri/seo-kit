import { pathToFileURL } from "node:url";

export async function fetchReleases(repository, request = fetch) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(repository)) throw new Error("Invalid release repository");
  const response = await request(`https://api.github.com/repos/${repository}/releases?per_page=100`, {
    headers: { Accept: "application/vnd.github+json", "User-Agent": "seo-kit-updater" },
    credentials: "omit",
    redirect: "error",
    signal: AbortSignal.timeout(25_000),
  });
  if (!response.ok) throw new Error(`Public release lookup failed (HTTP ${response.status}). Retaining the installed version`);
  const releases = await response.json();
  if (!Array.isArray(releases)) throw new Error("Invalid release API response");
  return releases;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    process.stdout.write(JSON.stringify(await fetchReleases(process.argv[2])));
  } catch (error) {
    process.stderr.write(`Release lookup failed: ${error.message}\n`);
    process.exitCode = 1;
  }
}
