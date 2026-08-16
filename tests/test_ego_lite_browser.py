"""Regression coverage for the preferred Ego Lite browser provider."""

import pytest

from src.browser.base import BrowserActionClass, BrowserBackendUnavailableError
from src.browser.ego_lite import EgoLiteBackend, ego_lite_backend
from src.browser.provider import get_browser_backend
from src.core.config import settings


def test_ego_lite_space_name_is_stable_and_isolated():
    first = EgoLiteBackend._space_name("task:abc / unsafe")
    second = EgoLiteBackend._space_name("task:abc / unsafe")
    other = EgoLiteBackend._space_name("task:other")
    assert first == second
    assert first != other
    assert first.startswith("morrow-")
    assert ":" not in first
    assert "/" not in first


@pytest.mark.asyncio
async def test_ego_lite_click_cannot_be_downgraded_to_prepare():
    backend = EgoLiteBackend(executable="not-used")
    with pytest.raises(ValueError, match="minimal diklasifikasikan sebagai commit"):
        await backend.interact(
            "click",
            {"target": "@21"},
            task_space="task-1",
            action_class=BrowserActionClass.PREPARE,
        )


def test_browser_provider_can_select_ego_lite(monkeypatch):
    monkeypatch.setattr(settings, "browser_backend", "ego-lite")
    assert get_browser_backend() is ego_lite_backend


@pytest.mark.asyncio
async def test_ego_lite_unsupported_platform_without_binary_fails_cleanly(monkeypatch):
    backend = EgoLiteBackend(executable="definitely_missing_ego_browser_12345")
    monkeypatch.setattr("src.browser.ego_lite.platform.system", lambda: "Windows")
    monkeypatch.setattr("src.browser.ego_lite.shutil.which", lambda executable: None)
    with pytest.raises(BrowserBackendUnavailableError, match="macOS"):
        await backend.open("https://example.com", task_space="task-test")


@pytest.mark.asyncio
async def test_ego_lite_maps_open_and_fill_to_official_helpers(monkeypatch):
    backend = EgoLiteBackend(executable="not-used")
    scripts: list[str] = []

    async def capture_script(script: str):
        scripts.append(script)
        return {"success": True}

    monkeypatch.setattr(backend, "_run_script", capture_script)
    await backend.open("https://example.com", task_space="task-ego-1")
    await backend.interact(
        "fill",
        {"target": "@7", "value": "Bima"},
        task_space="task-ego-1",
        action_class=BrowserActionClass.PREPARE,
    )
    assert "useOrCreateTaskSpace" in scripts[0]
    assert "openOrReuseTab" in scripts[0]
    assert "https://example.com" in scripts[0]
    assert "fillInput" in scripts[1]
    assert '"@7"' in scripts[1]
    assert '"Bima"' in scripts[1]
