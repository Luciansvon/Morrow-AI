"""Narrow OpenViking HTTP adapter.

OpenViking is context infrastructure. It does not own Morrow routing, approvals, role authority,
or external-action policy. The adapter is disabled by default and deliberately exposes no secret
values in returned payloads or reprs.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from src.core.config import settings


class OpenVikingDisabledError(RuntimeError):
    """Raised when OpenViking is invoked while its feature flag is disabled."""


class OpenVikingClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        account: str | None = None,
        user: str | None = None,
        agent_id: str | None = None,
        timeout_seconds: float | None = None,
        enabled: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.enabled = settings.openviking_enabled if enabled is None else enabled
        self.base_url = (base_url or settings.openviking_base_url).rstrip("/")
        self._api_key = (
            api_key
            if api_key is not None
            else settings.openviking_api_key.get_secret_value().strip()
        )
        self.account = settings.openviking_account if account is None else account
        self.user = settings.openviking_user if user is None else user
        self.agent_id = settings.openviking_agent_id if agent_id is None else agent_id
        self.timeout_seconds = timeout_seconds or settings.openviking_timeout_seconds
        self._transport = transport

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise OpenVikingDisabledError("OpenViking integration disabled by feature flag.")
        if not self.base_url:
            raise ValueError("OpenViking base URL kosong.")
        if not self._api_key:
            raise ValueError("OpenViking API key belum dikonfigurasi.")

    def _headers(self, *, tenant_user: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-API-Key": self._api_key,
        }
        if self.agent_id:
            headers["X-OpenViking-Agent"] = self.agent_id
        if self.account:
            headers["X-OpenViking-Account"] = self.account
            resolved_user = (tenant_user or self.user).strip()
            if not resolved_user:
                raise ValueError(
                    "OpenViking root/account mode membutuhkan OPENVIKING_USER atau tenant_user."
                )
            headers["X-OpenViking-User"] = resolved_user
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        tenant_user: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        self._require_enabled()
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                method,
                path,
                headers=self._headers(tenant_user=tenant_user),
                params=params,
                json=json_body,
            )
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and payload.get("status") == "ok" and "result" in payload:
            return payload["result"]
        return payload

    async def health(self) -> dict[str, Any]:
        """Check server process health. This endpoint does not validate model readiness."""
        self._require_enabled()
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            response = await client.get("/health")
            response.raise_for_status()
            payload = response.json()
        return payload if isinstance(payload, dict) else {"status": str(payload)}

    async def find(
        self,
        query: str,
        *,
        target_uri: str | None = None,
        tenant_user: str | None = None,
    ) -> Any:
        """Semantic retrieval through OpenViking `/api/v1/search/find`."""
        if not query.strip():
            raise ValueError("OpenViking query tidak boleh kosong.")
        body: dict[str, Any] = {"query": query.strip()}
        if target_uri:
            if not target_uri.startswith("viking://"):
                raise ValueError("target_uri harus menggunakan skema viking://")
            body["target_uri"] = target_uri
        return await self._request(
            "POST",
            "/api/v1/search/find",
            tenant_user=tenant_user,
            json_body=body,
        )

    async def read(self, uri: str, *, tenant_user: str | None = None) -> Any:
        """Load exact context content from a `viking://` URI."""
        if not uri.startswith("viking://"):
            raise ValueError("OpenViking read hanya menerima URI viking://")
        return await self._request(
            "GET",
            "/api/v1/content/read",
            tenant_user=tenant_user,
            params={"uri": uri},
        )

    async def add_remote_resource(
        self,
        path: str,
        *,
        to: str | None = None,
        parent: str | None = None,
        reason: str | None = None,
        wait: bool = True,
        tenant_user: str | None = None,
    ) -> Any:
        """Add a remote HTTP(S) resource.

        This mutates OpenViking and therefore must only be called through an approved Morrow
        COMMIT path. Local file upload is intentionally not implemented here because it requires
        the dedicated temporary-upload flow and explicit file-scope authorization.
        """
        parsed = urlparse(path)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OpenViking remote resource harus berupa URL HTTP(S) valid.")
        if to and parent:
            raise ValueError("Gunakan salah satu `to` atau `parent`, bukan keduanya.")
        if to and not to.startswith("viking://"):
            raise ValueError("`to` harus menggunakan URI viking://")
        if parent and not parent.startswith("viking://"):
            raise ValueError("`parent` harus menggunakan URI viking://")
        body: dict[str, Any] = {"path": path, "wait": bool(wait)}
        if to:
            body["to"] = to
        if parent:
            body["parent"] = parent
            body["create_parent"] = True
        if reason:
            body["reason"] = reason[:1000]
        return await self._request(
            "POST",
            "/api/v1/resources",
            tenant_user=tenant_user,
            json_body=body,
        )


openviking_client = OpenVikingClient()
