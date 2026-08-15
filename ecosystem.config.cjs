const isWindows = process.platform === "win32";
const python = process.env.MORROW_PYTHON || (isWindows ? "python.exe" : "python3");
const usesWindowsPythonShim = isWindows && !python.includes("/") && !python.includes("\\");

module.exports = {
  apps: [
    {
      name: "morrow",
      cwd: __dirname,
      script: usesWindowsPythonShim ? "scripts/run_morrow_python.cjs" : "morrow_runtime.py",
      interpreter: usesWindowsPythonShim ? process.execPath : python,
      interpreter_args: [],
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      exp_backoff_restart_delay: 1000,
      kill_timeout: 10000,
      time: true,
      env: {
        PYTHONUNBUFFERED: "1",
        CHANNEL_ADAPTER: "telegram",
      },
    },
  ],
};
