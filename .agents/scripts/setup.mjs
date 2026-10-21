#!/usr/bin/env node
import path from "node:path";
import { ROOT, managedLinks, removeManagedLink } from "./lib.mjs";
import { installation, installGlobal, syncGlobal, removeGlobal, rollbackGlobal, readInstallation, checkInstallation } from "./global-install.mjs";
import { retireKnowledgeServices, retireLegacySync } from "./retire-knowledge-services.mjs";

const requestedAction = process.argv[2] ?? "install";
const action = requestedAction === "uninstall" ? "remove" : requestedAction;
const options = { dryRun: process.argv.includes("--dry-run"), noServices: process.argv.includes("--no-services") };
// installation() resolves the stable launcher's SEO_KIT_MANAGED_BASE for all actions.
try {
  for (const flag of process.argv.slice(3)) if (!["--dry-run", "--no-services", "--legacy"].includes(flag)) throw new Error(`Unknown option: ${flag}`);
  if (options.dryRun && !["install", "links", "remove"].includes(action)) throw new Error(`--dry-run is not supported for ${action}. No action performed`);
  if (options.noServices && !["install", "links"].includes(action)) throw new Error(`--no-services is only supported for installation`);
  if (process.argv.includes("--legacy")) {
    if (action !== "remove") throw new Error("--legacy is only supported by setup:remove");
    retireKnowledgeServices({ dryRun: options.dryRun });
    retireLegacySync({ root: ROOT, dryRun: options.dryRun });
    let count = 0;
    for (const [link, target] of managedLinks()) if (removeManagedLink(link, target, options.dryRun)) count++;
    console.log(`legacy: ${options.dryRun ? "would remove" : "removed"} ${count} links owned by ${ROOT}. Other resources preserved`);
  } else if (action === "install" || action === "links") installGlobal({ ...options, noServices: options.noServices || action === "links" });
  else if (action === "sync") syncGlobal(options);
  else if (action === "rollback") rollbackGlobal(options);
  else if (action === "remove") {
    if (options.dryRun) console.log(`remove: would remove managed integrations and scheduler at ${installation(options).base}, including all managed releases, logs and the installation directory`);
    else {
      removeGlobal(options);
      console.log("uninstall: PASS. Managed integrations, automatic updates, releases, logs and installation directory removed. Open a new assistant session to refresh discovery.");
    }
  } else if (action === "status") {
    const ctx = installation(options);
    const state = readInstallation(ctx);
    const errors = checkInstallation(ctx, state);
    if (state) console.log(`installation: ${ctx.base}\nrelease: ${state.commit}\napproval: ${state.approval ? `${state.approval.tag} (release ${state.approval.id})` : "legacy/unrecorded, migration required"}\nupdates configured: ${state.scheduler ?? "disabled"}\nlog: ${path.join(ctx.base, "state/updates.log")}`);
    if (state?.schedulerError) errors.push(`Automatic updates NOT confirmed: ${state.schedulerError}`);
    if (errors.length) throw new Error(errors.join("\n"));
    console.log("setup: PASS (files verified, host discovery and scheduler execution require host checks)");
  } else throw new Error(`Unknown action: ${action}`);
} catch (error) {
  console.error(`setup: FAIL: ${error.message}`);
  process.exitCode = 1;
}
