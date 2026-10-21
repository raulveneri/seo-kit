import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { nextLocalMidnightDelay } from "../scripts/update-clock.mjs";

test("watch mode schedules local midnight across time zones and daylight saving changes", () => {
  const cases = [
    ["UTC", "2026-10-21T23:59:59Z", 1000],
    ["Asia/Kathmandu", "2026-10-21T18:14:59Z", 1000],
    ["Europe/Madrid", "2026-03-28T23:00:00Z", 23 * 3600_000],
    ["Europe/Madrid", "2026-10-24T22:00:00Z", 25 * 3600_000],
  ];
  for (const [TZ, timestamp, expected] of cases) {
    const source = `const delay = ${nextLocalMidnightDelay.toString()}; process.stdout.write(String(delay(new Date(${JSON.stringify(timestamp)}))));`;
    const result = spawnSync(process.execPath, ["-e", source], { env: { ...process.env, TZ }, encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(Number(result.stdout), expected, `${TZ}: ${timestamp}`);
  }
});
