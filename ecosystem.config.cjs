const isWindows = process.platform === "win32";
const python = process.env.MORROW_PYTHON || (isWindows ? "python.exe" : "python3");
const usesWindowsCommandAlias = isWindows && !python.includes("/") && !python.includes("\\");

module.exports = {
  apps: [
    {
      name: "morrow",
      cwd: __dirname,
      script: "morrow_runtime.py",
      interpreter: usesWindowsCommandAlias ? "cmd.exe" : python,
      interpreter_args: usesWindowsCommandAlias ? ["/d", "/c", python] : [],
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
