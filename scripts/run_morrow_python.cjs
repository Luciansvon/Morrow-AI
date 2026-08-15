"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const python = process.env.MORROW_PYTHON || "python.exe";
const runtime = path.join(projectRoot, "morrow_runtime.py");

const child = spawn(python, [runtime], {
  cwd: projectRoot,
  env: process.env,
  stdio: "inherit",
  windowsHide: true,
});

let settled = false;

child.once("error", (error) => {
  if (settled) return;
  settled = true;
  console.error(`Morrow Python gagal dijalankan: ${error.message}`);
  process.exitCode = 1;
});

child.once("exit", (code, signal) => {
  if (settled) return;
  settled = true;
  if (signal) {
    console.error(`Morrow Python berhenti karena signal ${signal}.`);
    process.exitCode = 1;
    return;
  }
  process.exitCode = code ?? 1;
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
