#!/usr/bin/env node
import { syncGlobal } from "./global-install.mjs";
const action = process.argv[2] ?? "once";
function sync() {
  try { syncGlobal(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
if (action === "once") sync();
else if (action === "watch") {
  sync();
  setInterval(() => { process.exitCode = 0; sync(); }, 3_600_000);
} else throw new Error(`Unknown action: ${action}`);
