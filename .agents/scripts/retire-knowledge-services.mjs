import { existsSync, readFileSync, unlinkSync } from "node:fs";
import path from "node:path";
import { HOME, MARKER, run } from "./lib.mjs";

// Also runs during link-only synchronization, so existing installations migrate.
export function retireKnowledgeServices({ home = HOME, platform = process.platform, dryRun = false, execute = run, report = console.log } = {}) {
  const names = platform === "linux"
    ? ["seo-kit-refresh.timer", "seo-kit-refresh.service"]
    : platform === "darwin" ? ["com.seo-kit.refresh.plist"] : [];
  const directory = platform === "linux"
    ? path.join(home, ".config", "systemd", "user")
    : path.join(home, "Library", "LaunchAgents");
  let removed = false;
  for (const name of names) {
    const target = path.join(directory, name);
    if (!existsSync(target) || !readFileSync(target, "utf8").includes(MARKER)) continue;
    if (dryRun) {
      report(`services: would retire ${target}`);
      continue;
    }
    if (platform === "linux") {
      execute("systemctl", ["--user", "disable", "--now", name]);
    } else {
      // bootout also returns nonzero when the job is already unloaded.
      const domain = `gui/${process.getuid()}`;
      const result = execute("launchctl", ["bootout", domain, target], { allowFailure: true });
      if (result.status !== 0) {
        const loaded = execute("launchctl", ["print", `${domain}/com.seo-kit.refresh`], { allowFailure: true });
        if (loaded.status === 0) throw new Error("Cannot stop the legacy knowledge refresh job");
      }
    }
    unlinkSync(target);
    removed = true;
    report(`services: retired ${target}`);
  }
  if (removed && platform === "linux") execute("systemctl", ["--user", "daemon-reload"]);
}

// Explicit legacy migration only. Never stop a job owned by another checkout.
export function retireLegacySync({ root, home = HOME, platform = process.platform, dryRun = false, execute = run, report = console.log } = {}) {
  if (!root || !["linux", "darwin"].includes(platform)) return;
  const file = platform === "linux"
    ? path.join(home, ".config/systemd/user/seo-kit-sync.service")
    : path.join(home, "Library/LaunchAgents/com.seo-kit.sync.plist");
  const escapedRoot = root.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  if (!existsSync(file)) return;
  const content = readFileSync(file, "utf8");
  if (!content.includes(MARKER) || ![root, escapedRoot].some((value) => content.includes(`${value}/.agents/scripts/remote-sync.mjs`))) return;
  if (dryRun) { report(`legacy: would stop and remove ${file}`); return; }
  if (platform === "linux") execute("systemctl", ["--user", "disable", "--now", "seo-kit-sync.service"]);
  else {
    const domain = `gui/${process.getuid()}`;
    const stopped = execute("launchctl", ["bootout", domain, file], { allowFailure: true });
    if (stopped.status !== 0 && execute("launchctl", ["print", `${domain}/com.seo-kit.sync`], { allowFailure: true }).status === 0) throw new Error("Cannot stop legacy sync job");
  }
  unlinkSync(file);
  if (platform === "linux") execute("systemctl", ["--user", "daemon-reload"]);
  report(`legacy: retired ${file}`);
}
