import { homedir } from "node:os";
import path from "node:path";

// Native assistant discovery paths are separate from the kit's data directory.
export function platformPaths({ platform = process.platform, home = homedir(), env = process.env } = {}) {
  const p = platform === "win32" ? path.win32 : path.posix;
  const absolute = (value, fallback) => value && p.isAbsolute(value) ? value : fallback;
  // Packaged Windows hosts can virtualize LocalAppData into a private cache.
  // Keep managed data under the user profile so external tools see the same files.
  const data = platform === "win32"
    ? p.join(home, ".local", "share")
    : platform === "darwin" ? p.join(home, "Library", "Application Support")
      : absolute(env.XDG_DATA_HOME, p.join(home, ".local", "share"));
  const config = absolute(env.XDG_CONFIG_HOME, p.join(home, ".config"));
  return {
    base: p.join(data, "ai-kits", "seo-kit"),
    sharedSkills: p.join(home, ".agents", "skills"),
    claude: absolute(env.CLAUDE_CONFIG_DIR, p.join(home, ".claude")),
    codex: absolute(env.CODEX_HOME, p.join(home, ".codex")),
    opencode: p.join(config, "opencode"),
    opencodeResources: absolute(env.OPENCODE_CONFIG_DIR, p.join(config, "opencode")),
    config,
  };
}
