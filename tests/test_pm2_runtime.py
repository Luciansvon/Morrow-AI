"""Regression tests for the PM2 runtime entrypoint."""

from pathlib import Path

import morrow_runtime


def test_root_runtime_wrapper_is_importable_without_starting_bot():
    assert callable(morrow_runtime.run)


def test_pm2_points_to_root_runtime_wrapper():
    config = Path("ecosystem.config.cjs").read_text(encoding="utf-8")
    assert 'script: "morrow_runtime.py"' in config
    assert 'script: "src/main.py"' not in config


def test_pm2_has_windows_python_alias_fallback():
    config = Path("ecosystem.config.cjs").read_text(encoding="utf-8")
    assert 'interpreter: usesWindowsCommandAlias ? "cmd.exe" : python' in config
    assert '"/d", "/c", python' in config
