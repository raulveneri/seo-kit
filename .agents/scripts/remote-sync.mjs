#!/usr/bin/env node
import { syncGlobal } from "./global-install.mjs";
import { nextLocalMidnightDelay } from "./update-clock.mjs";
const action = process.argv[2] ?? "once";
function sync() {
  try { syncGlobal(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
if (action === "once") sync();
else if (action === "watch") {
  sync();
  function schedule() {
    setTimeout(() => { process.exitCode = 0; sync(); schedule(); }, nextLocalMidnightDelay());
  }
  schedule();
} else throw new Error(`Unknown action: ${action}`);
