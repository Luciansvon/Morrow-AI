"""Read-focused Immich adapter for Morrow media context.

Immich owns media binaries and media-native metadata. Morrow/OpenViking may keep references to
Immich assets, but this module intentionally does not mirror original media into general memory.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from src.core.config import settings

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


class ImmichDisabledError(RuntimeError):
    """Raised when Immich is invoked while its feature flag is disabled."""


@dataclass(frozen=True)
class MediaAssetReference:
    """Serializable reference suitable for context storage without copying the media binary."""

    provider: str
    asset_id: str
    asset_type: str | None = None
    original_file_name: str | None = None
    original_mime_type: str | None = None
    file_created_at: str | None = None
    description: str | None = None

    @property
    def uri(self) -> str:
        return f"immich://asset/{self.asset_id}"

    def to_context_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["uri"] = self.uri
        return record


class ImmichClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        enabled: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.enabled = settings.immich_enabled if enabled is None else enabled
        raw_base = (base_url or settings.immich_base_url).rstrip("/")
        self.api_url = raw_base if raw_base.endswith("/api") else f"{raw_base}/api"
        self._api_key = (
            api_key if api_key is not None else settings.immich_api_key.get_secret_value().strip()
        )
        self.timeout_seconds = timeout_seconds or settings.immich_timeout_seconds
        self._transport = transport

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise ImmichDisabledError("Immich integration disabled by feature flag.")
        if not self.api_url:
            raise ValueError("Immich base URL kosong.")
        if not self._api_key:
            raise ValueError("Immich API key belum dikonfigurasi.")

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
        }

    @staticmethod
    def _validate_asset_id(asset_id: str) -> str:
        asset_id = asset_id.strip()
        if not _UUID_RE.fullmatch(asset_id):
            raise ValueError("Immich asset_id harus UUID valid.")
        return asset_id

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        self._require_enabled()
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.api_url,
            timeout=timeout,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                method,
                path,
                headers=self._headers() if authenticated else {"Accept": "application/json"},
                params=params,
                json=json_body,
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    async def health(self) -> dict[str, Any]:
        """Check the public Immich server ping endpoint."""
        self._require_enabled()
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.api_url,
            timeout=timeout,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            response = await client.get("/server/ping", headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        return payload if isinstance(payload, dict) else {"res": str(payload)}

    async def search_assets(
        self,
        *,
        page: int = 1,
        size: int | None = None,
        with_exif: bool = True,
        with_people: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> Any:
        """Search/paginate assets through Immich metadata search.

        Ownership scope is intentionally not client-supplied; the API key's server-side
        permissions/user scope remains authoritative.
        """
        resolved_size = size or settings.immich_default_search_size
        if page < 1:
            raise ValueError("Immich search page minimal 1.")
        if not 1 <= resolved_size <= 1000:
            raise ValueError("Immich search size harus 1..1000.")
        body: dict[str, Any] = {
            "page": page,
            "size": resolved_size,
            "withExif": bool(with_exif),
            "withPeople": bool(with_people),
        }
        for key, value in (filters or {}).items():
            if key in {"userIds", "ownerId", "ownerIds"}:
                raise ValueError("Ownership scope Immich tidak boleh dikontrol oleh model/client.")
            body[key] = value
        return await self._request("POST", "/search/metadata", json_body=body)

    async def smart_search(
        self,
        query: str,
        *,
        page: int = 1,
        size: int | None = None,
        with_people: bool = False,
    ) -> Any:
        """Contextual CLIP search without copying assets out of Immich."""
        query = query.strip()
        if not query:
            raise ValueError("Immich smart-search query tidak boleh kosong.")
        resolved_size = size or settings.immich_default_search_size
        if page < 1 or not 1 <= resolved_size <= 1000:
            raise ValueError("Immich smart-search page/size tidak valid.")
        return await self._request(
            "POST",
            "/search/smart",
            json_body={
                "query": query,
                "page": page,
                "size": resolved_size,
                "withPeople": bool(with_people),
            },
        )

    async def get_asset(self, asset_id: str) -> dict[str, Any]:
        asset_id = self._validate_asset_id(asset_id)
        payload = await self._request("GET", f"/assets/{asset_id}")
        if not isinstance(payload, dict):
            raise ValueError("Respons asset Immich tidak valid.")
        return payload

    async def get_asset_metadata(self, asset_id: str) -> Any:
        asset_id = self._validate_asset_id(asset_id)
        return await self._request("GET", f"/assets/{asset_id}/metadata")

    @staticmethod
    def reference_from_asset(asset: dict[str, Any]) -> MediaAssetReference:
        asset_id = str(asset.get("id") or "").strip()
        ImmichClient._validate_asset_id(asset_id)
        return MediaAssetReference(
            provider="immich",
            asset_id=asset_id,
            asset_type=str(asset.get("type")) if asset.get("type") is not None else None,
            original_file_name=(
                str(asset.get("originalFileName"))
                if asset.get("originalFileName") is not None
                else None
            ),
            original_mime_type=(
                str(asset.get("originalMimeType"))
                if asset.get("originalMimeType") is not None
                else None
            ),
            file_created_at=(
                str(asset.get("fileCreatedAt")) if asset.get("fileCreatedAt") is not None else None
            ),
            description=(
                str(asset.get("exifInfo", {}).get("description"))
                if isinstance(asset.get("exifInfo"), dict)
                and asset.get("exifInfo", {}).get("description") is not None
                else None
            ),
        )


immich_client = ImmichClient()
