"""LLM-facing tools for feature-flagged OpenViking and Immich integrations."""

from __future__ import annotations

from typing import Any

from src.core.config import settings
from src.integrations.immich import immich_client
from src.integrations.openviking import openviking_client
from src.tools.registry import ToolCapability, tool_registry


async def openviking_find(query: str, target_uri: str | None = None) -> Any:
    """Search authorized OpenViking context."""
    return await openviking_client.find(query, target_uri=target_uri)


async def openviking_read(uri: str) -> Any:
    """Read an exact authorized viking:// context URI."""
    return await openviking_client.read(uri)


async def openviking_add_resource(
    path: str,
    to: str | None = None,
    parent: str | None = None,
    reason: str | None = None,
    wait: bool = True,
) -> Any:
    """Add a remote resource to OpenViking after Morrow approval."""
    return await openviking_client.add_remote_resource(
        path,
        to=to,
        parent=parent,
        reason=reason,
        wait=wait,
    )


def _compact_immich_asset(asset: dict[str, Any]) -> dict[str, Any]:
    reference = immich_client.reference_from_asset(asset)
    compact: dict[str, Any] = reference.to_context_record()
    for key in (
        "localDateTime",
        "isFavorite",
        "isArchived",
        "isTrashed",
        "visibility",
        "duration",
    ):
        if key in asset:
            compact[key] = asset[key]
    exif = asset.get("exifInfo")
    if isinstance(exif, dict):
        allowed_exif = {
            key: exif[key]
            for key in (
                "city",
                "state",
                "country",
                "dateTimeOriginal",
                "description",
                "make",
                "model",
                "lensModel",
            )
            if exif.get(key) is not None
        }
        if allowed_exif:
            compact["exif"] = allowed_exif
    return compact


async def immich_search_assets(
    query: str | None = None,
    page: int = 1,
    size: int | None = None,
    with_exif: bool = True,
) -> dict[str, Any]:
    """Search authorized Immich media and return compact references, never media binaries."""
    if query and query.strip():
        payload = await immich_client.smart_search(query, page=page, size=size)
    else:
        payload = await immich_client.search_assets(page=page, size=size, with_exif=with_exif)
    if not isinstance(payload, dict):
        return {"raw": payload, "assets": []}
    asset_bucket = payload.get("assets")
    if isinstance(asset_bucket, dict):
        items = asset_bucket.get("items") or []
    elif isinstance(payload.get("items"), list):
        items = payload.get("items") or []
    else:
        items = []
    compact = [
        _compact_immich_asset(item)
        for item in items
        if isinstance(item, dict) and item.get("id")
    ]
    return {
        "assets": compact,
        "count": len(compact),
        "next_page": asset_bucket.get("nextPage") if isinstance(asset_bucket, dict) else None,
    }


async def immich_get_asset(asset_id: str, include_metadata: bool = False) -> dict[str, Any]:
    """Get one authorized Immich asset as metadata/reference only."""
    asset = await immich_client.get_asset(asset_id)
    result = _compact_immich_asset(asset)
    if include_metadata:
        result["metadata"] = await immich_client.get_asset_metadata(asset_id)
    return result


def ensure_integration_tools_registered() -> None:
    if settings.openviking_enabled:
        if tool_registry.get_tool("openviking_find") is None:
            tool_registry.register_tool(
                "openviking_find",
                openviking_find,
                description=(
                    "Cari context/memory/knowledge yang sudah diizinkan di OpenViking. "
                    "Gunakan target_uri viking:// bila scope sudah diketahui."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "target_uri": {"type": "string", "pattern": "^viking://"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                domain="context",
                capability=ToolCapability.READ,
                risk="low",
                side_effect=False,
                auth_required=True,
                output_trust="untrusted_external",
                cost_class="network",
                retry_safe=True,
                keywords={"openviking", "memory", "context", "knowledge", "skill", "experience", "recall"},
            )
        if tool_registry.get_tool("openviking_read") is None:
            tool_registry.register_tool(
                "openviking_read",
                openviking_read,
                description="Baca context OpenViking dari URI viking:// yang sudah ditemukan.",
                parameters={
                    "type": "object",
                    "properties": {"uri": {"type": "string", "pattern": "^viking://"}},
                    "required": ["uri"],
                    "additionalProperties": False,
                },
                domain="context",
                capability=ToolCapability.READ,
                risk="low",
                side_effect=False,
                auth_required=True,
                output_trust="untrusted_external",
                cost_class="network",
                retry_safe=True,
                keywords={"openviking", "read", "context", "viking"},
            )
        if tool_registry.get_tool("openviking_add_resource") is None:
            tool_registry.register_tool(
                "openviking_add_resource",
                openviking_add_resource,
                description=(
                    "Tambahkan URL HTTP(S) ke OpenViking. Ini mengubah knowledge store dan wajib approval user."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "pattern": "^https?://"},
                        "to": {"type": "string", "pattern": "^viking://"},
                        "parent": {"type": "string", "pattern": "^viking://"},
                        "reason": {"type": "string", "maxLength": 1000},
                        "wait": {"type": "boolean"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                domain="context",
                capability=ToolCapability.COMMIT,
                risk="medium",
                side_effect=True,
                auth_required=True,
                output_trust="untrusted_external",
                cost_class="network",
                retry_safe=False,
                keywords={"openviking", "index", "ingest", "resource", "knowledge"},
            )

    if settings.immich_enabled:
        if tool_registry.get_tool("immich_search_assets") is None:
            tool_registry.register_tool(
                "immich_search_assets",
                immich_search_assets,
                description=(
                    "Cari foto/video yang diizinkan di Immich dan kembalikan reference + metadata ringkas, bukan binary."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "page": {"type": "integer", "minimum": 1},
                        "size": {"type": "integer", "minimum": 1, "maximum": 1000},
                        "with_exif": {"type": "boolean"},
                    },
                    "additionalProperties": False,
                },
                domain="media",
                capability=ToolCapability.READ,
                risk="low",
                side_effect=False,
                auth_required=True,
                output_trust="untrusted_external",
                cost_class="network",
                retry_safe=True,
                keywords={"immich", "photo", "foto", "image", "video", "media", "asset", "gallery"},
            )
        if tool_registry.get_tool("immich_get_asset") is None:
            tool_registry.register_tool(
                "immich_get_asset",
                immich_get_asset,
                description=(
                    "Ambil metadata/reference satu asset Immich yang diizinkan. Binary asli tetap di Immich."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "asset_id": {"type": "string", "format": "uuid"},
                        "include_metadata": {"type": "boolean"},
                    },
                    "required": ["asset_id"],
                    "additionalProperties": False,
                },
                domain="media",
                capability=ToolCapability.READ,
                risk="low",
                side_effect=False,
                auth_required=True,
                output_trust="untrusted_external",
                cost_class="network",
                retry_safe=True,
                keywords={"immich", "asset", "metadata", "photo", "video"},
            )
