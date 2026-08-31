"""Small synchronous JSON HTTP client for upstream APIs."""

from __future__ import annotations

from typing import Protocol

import httpx2

from .errors import ProviderRequestError
from .models import JsonObject


class JsonHttpClientProtocol(Protocol):
    def get_json(self, url: str, params: dict[str, str], provider: str) -> JsonObject: ...


class JsonHttpClient:
    def __init__(self, timeout_seconds: float = 30) -> None:
        self._timeout_seconds = timeout_seconds

    def get_json(self, url: str, params: dict[str, str], provider: str) -> JsonObject:
        try:
            with httpx2.Client(timeout=self._timeout_seconds) as client:
                response = client.get(
                    url,
                    params=params,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "social-connectors-api/1.1",
                    },
                )
            response.raise_for_status()
        except httpx2.TimeoutException:
            raise ProviderRequestError(provider, None, f"Request ke {provider} timeout") from None
        except httpx2.HTTPStatusError as exc:
            raise ProviderRequestError(
                provider,
                exc.response.status_code,
                f"{provider} menolak request",
            ) from None
        except httpx2.RequestError:
            raise ProviderRequestError(
                provider,
                None,
                f"{provider} tidak dapat dihubungi",
            ) from None

        try:
            payload = response.json()
        except ValueError:
            raise ProviderRequestError(
                provider,
                response.status_code,
                f"{provider} mengembalikan JSON yang tidak valid",
            ) from None
        if not isinstance(payload, dict):
            raise ProviderRequestError(
                provider,
                response.status_code,
                f"{provider} mengembalikan struktur yang tidak dikenal",
            )
        return payload
