"""Regression tests for the PM2 runtime entrypoint."""

from pathlib import Path

import morrow_runtime


def test_root_runtime_wrapper_is_importable_without_starting_bot():
    assert callable(morrow_runtime.run)


def test_pm2_points_to_root_runtime_wrapper():
    config = Path("ecosystem.config.cjs").read_text(encoding="utf-8")
    assert 'script: usesWindowsPythonShim ? "scripts/run_morrow_python.cjs" : "morrow_runtime.py"' in config
    assert 'script: "src/main.py"' not in config


def test_pm2_has_windows_python_alias_fallback():
    config = Path("ecosystem.config.cjs").read_text(encoding="utf-8")
    assert 'interpreter: usesWindowsPythonShim ? process.execPath : python' in config
    assert 'const usesWindowsPythonShim = isWindows' in config


def test_windows_python_shim_spawns_the_root_runtime():
    shim = Path("scripts/run_morrow_python.cjs").read_text(encoding="utf-8")
    assert 'spawn(python, [runtime]' in shim
    assert 'path.join(projectRoot, "morrow_runtime.py")' in shim
