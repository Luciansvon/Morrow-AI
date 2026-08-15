const path = require("path");

module.exports = {
  apps: [
    {
      name: "morrow",
      cwd: __dirname,
      script: path.join("src", "main.py"),
      interpreter:
        process.env.MORROW_PYTHON ||
        (process.platform === "win32" ? "python" : "python3"),
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
