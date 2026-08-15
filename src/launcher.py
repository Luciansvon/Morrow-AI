"""PM2-backed command launcher for Morrow."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "morrow"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_CONFIG = PROJECT_ROOT / "ecosystem.config.cjs"
WINDOWS_STARTUP_SCRIPT = PROJECT_ROOT / "scripts" / "install_pm2_startup.ps1"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="MORROW",
        description="Start and manage Morrow through PM2.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=("start", "status", "logs", "restart", "stop", "delete", "foreground", "startup"),
    )
    return parser


def _find_pm2() -> str:
    pm2 = shutil.which("pm2") or shutil.which("pm2.cmd")
    if pm2:
        return pm2
    raise FileNotFoundError(
        "PM2 belum terpasang. Install sekali dengan `npm install -g pm2`, lalu jalankan MORROW lagi."
    )


def _pm2_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MORROW_PYTHON"] = _resolve_python_interpreter()
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _resolve_python_interpreter() -> str:
    """Return an interpreter PM2 can spawn in the active Python environment."""
    executable = Path(sys.executable)
    candidates = (executable,)
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.stat().st_size > 0:
                return str(candidate)
        except OSError:
            continue

    # Microsoft Store Python exposes a zero-byte app-execution alias. Windows
    # can launch the command name, but PM2 cannot spawn the alias by absolute path.
    if os.name == "nt":
        if shutil.which("python.exe"):
            return "python.exe"
        if shutil.which("python"):
            return "python"

    candidates = (
        Path(sys.prefix) / "python.exe",
        Path(sys.base_prefix) / "python.exe",
    )
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.stat().st_size > 0:
                return str(candidate)
        except OSError:
            continue
    return sys.executable


def _run_pm2(
    pm2: str,
    args: list[str],
    *,
    env: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [pm2, *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=check,
        text=True,
    )


def _is_managed(pm2: str, env: dict[str, str]) -> bool:
    result = subprocess.run(
        [pm2, "describe", APP_NAME],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _start(pm2: str, env: dict[str, str]) -> None:
    if not ECOSYSTEM_CONFIG.exists():
        raise FileNotFoundError(f"Config PM2 tidak ditemukan: {ECOSYSTEM_CONFIG}")
    if _is_managed(pm2, env):
        _run_pm2(pm2, ["restart", APP_NAME, "--update-env"], env=env)
    else:
        _run_pm2(pm2, ["start", str(ECOSYSTEM_CONFIG), "--only", APP_NAME], env=env)
    if not _is_managed(pm2, env):
        raise RuntimeError(
            "PM2 tidak berhasil mendaftarkan process morrow. Cek detailnya dengan `pm2 logs morrow`."
        )
    _run_pm2(pm2, ["save"], env=env)
    print("\nMorrow aktif di PM2. Terminal boleh ditutup.")
    print("   Cek status: MORROW status")
    print("   Lihat log : MORROW logs")


def _foreground() -> None:
    from src.main import main

    asyncio.run(main())


def _install_startup(pm2: str, env: dict[str, str]) -> None:
    _start(pm2, env)
    if os.name == "nt":
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            raise FileNotFoundError("PowerShell tidak ditemukan untuk memasang startup task Windows.")
        if not WINDOWS_STARTUP_SCRIPT.exists():
            raise FileNotFoundError(f"Startup script tidak ditemukan: {WINDOWS_STARTUP_SCRIPT}")
        subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WINDOWS_STARTUP_SCRIPT),
                "-Pm2Path",
                pm2,
            ],
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
        )
        return

    result = _run_pm2(pm2, ["startup"], env=env, check=False)
    if result.returncode != 0:
        print("PM2 startup belum selesai. Jalankan command privileged yang dicetak PM2, lalu ulangi `pm2 save`.")
    else:
        print("✅ Startup hook PM2 diproses. Jika PM2 mencetak command sudo, jalankan command itu sekali.")


def run_cli(argv: list[str] | None = None) -> int:
    command = _build_parser().parse_args(argv).command
    if command == "foreground":
        _foreground()
        return 0

    try:
        pm2 = _find_pm2()
        env = _pm2_env()
        if command == "start":
            _start(pm2, env)
        elif command == "status":
            _run_pm2(pm2, ["status", APP_NAME], env=env, check=False)
        elif command == "logs":
            _run_pm2(pm2, ["logs", APP_NAME], env=env, check=False)
        elif command == "restart":
            _run_pm2(pm2, ["restart", APP_NAME, "--update-env"], env=env)
            _run_pm2(pm2, ["save"], env=env)
        elif command == "stop":
            _run_pm2(pm2, ["stop", APP_NAME], env=env)
            _run_pm2(pm2, ["save"], env=env)
        elif command == "delete":
            _run_pm2(pm2, ["delete", APP_NAME], env=env)
            _run_pm2(pm2, ["save"], env=env)
        elif command == "startup":
            _install_startup(pm2, env)
        return 0
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


def cli_main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    cli_main()
