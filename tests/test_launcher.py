"""Tests for the PM2-backed MORROW launcher."""

from pathlib import Path

from src import launcher


def test_parser_defaults_to_start():
    args = launcher._build_parser().parse_args([])
    assert args.command == "start"


def test_start_launches_ecosystem_then_saves(monkeypatch):
    calls: list[list[str]] = []
    env = {"MORROW_PYTHON": "python"}

    managed_states = iter((False, True))
    monkeypatch.setattr(launcher, "_is_managed", lambda pm2, active_env: next(managed_states))
    monkeypatch.setattr(
        launcher,
        "_run_pm2",
        lambda pm2, args, *, env, check=True: calls.append(args),
    )
    monkeypatch.setattr(Path, "exists", lambda self: True)

    launcher._start("pm2", env)

    assert calls[0][0] == "start"
    assert str(launcher.ECOSYSTEM_CONFIG) in calls[0]
    assert calls[1] == ["save"]


def test_start_restarts_existing_process(monkeypatch):
    calls: list[list[str]] = []
    env = {"MORROW_PYTHON": "python"}

    managed_states = iter((True, True))
    monkeypatch.setattr(launcher, "_is_managed", lambda pm2, active_env: next(managed_states))
    monkeypatch.setattr(
        launcher,
        "_run_pm2",
        lambda pm2, args, *, env, check=True: calls.append(args),
    )
    monkeypatch.setattr(Path, "exists", lambda self: True)

    launcher._start("pm2", env)

    assert calls[0] == ["restart", "morrow", "--update-env"]
    assert calls[1] == ["save"]


def test_foreground_does_not_require_pm2(monkeypatch):
    called = []
    monkeypatch.setattr(launcher, "_foreground", lambda: called.append(True))
    monkeypatch.setattr(launcher, "_find_pm2", lambda: (_ for _ in ()).throw(AssertionError))

    assert launcher.run_cli(["foreground"]) == 0
    assert called == [True]


def test_pm2_env_resolves_windows_store_python_alias(monkeypatch, tmp_path):
    alias = tmp_path / "WindowsApps" / "python.exe"
    alias.parent.mkdir()
    alias.write_bytes(b"")
    real_python = tmp_path / "Python312" / "python.exe"
    real_python.parent.mkdir()
    real_python.write_bytes(b"python")

    monkeypatch.setattr(launcher.sys, "executable", str(alias))
    monkeypatch.setattr(launcher.sys, "prefix", str(real_python.parent))

    monkeypatch.setattr(launcher.os, "name", "nt")
    monkeypatch.setattr(launcher.shutil, "which", lambda command: str(alias) if command == "python.exe" else None)

    assert launcher._pm2_env()["MORROW_PYTHON"] == "python.exe"
