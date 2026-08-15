"""Remote embedding client with deterministic mock mode for tests."""

import hashlib
import math
import re

import httpx

from src.core.config import settings

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class MemoryEmbeddingProvider:
    @staticmethod
    def _mock_embedding(text: str, dimensions: int) -> list[float]:
        """Tiny deterministic hashing vector used only with the configured mock API key."""
        vector = [0.0] * dimensions
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    async def embed_texts(self, texts: list[str]) -> list[list[float]] | None:
        if not texts or not settings.memory_semantic_enabled:
            return None
        bounded = [text[: settings.memory_embedding_max_chars] for text in texts]
        dimensions = settings.memory_embedding_dimensions
        api_key = settings.openrouter_api_key.get_secret_value().strip()
        if api_key.startswith("sk-mock"):
            return [self._mock_embedding(text, dimensions) for text in bounded]
        if not api_key:
            return None

        url = settings.openrouter_base_url.rstrip("/") + "/embeddings"
        payload = {
            "model": settings.memory_embedding_model,
            "input": bounded,
            "dimensions": dimensions,
            "encoding_format": "float",
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Luciansvon/Morrow-AI",
            "X-Title": "Morrow",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json().get("data") or []
        except (httpx.HTTPError, ValueError, TypeError):
            return None

        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        embeddings = [item.get("embedding") for item in ordered]
        if len(embeddings) != len(bounded):
            return None
        if any(not isinstance(vector, list) or len(vector) != dimensions for vector in embeddings):
            return None
        return [[float(value) for value in vector] for vector in embeddings]

    async def embed_text(self, text: str) -> list[float] | None:
        vectors = await self.embed_texts([text])
        return vectors[0] if vectors else None


memory_embedding_provider = MemoryEmbeddingProvider()
