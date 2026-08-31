"""Allowlisted execution for every endpoint in the checked-in registry."""

from __future__ import annotations

from typing import Any

from social_connectors_api.endpoint_registry import EndpointDefinition
from social_connectors_api.errors import ProviderRequestError
from social_connectors_api.http_client import JsonHttpClient, JsonHttpClientProtocol

from .ensembledata import EnsembleDataClient


class EnsembleDataCatalogProvider:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30,
        client: EnsembleDataClient | None = None,
    ) -> None:
        self._client = client or EnsembleDataClient(api_key, timeout_seconds)

    def execute(self, endpoint: EndpointDefinition, parameters: dict[str, Any]) -> dict[str, Any]:
        self._ensure_executable(endpoint)
        return self._client.get_json(endpoint.path, endpoint.validate_parameters(parameters))

    @staticmethod
    def _ensure_executable(endpoint: EndpointDefinition) -> None:
        if not endpoint.executable or endpoint.status != "ACTIVE":
            raise ValueError(f"Endpoint {endpoint.label} belum dapat dieksekusi")


class SerpApiCatalogProvider:
    base_url = "https://serpapi.com/search.json"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30,
        default_language: str = "id",
        default_country: str = "id",
        client: JsonHttpClientProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._default_language = default_language
        self._default_country = default_country
        self._client = client or JsonHttpClient(timeout_seconds)

    def execute(
        self, endpoint: EndpointDefinition, parameters: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        validated = endpoint.validate_parameters(parameters)
        query = validated.pop("query")
        limit = int(validated.pop("limit", "20"))
        validated.pop("sort", None)
        language = validated.pop("language", self._default_language)
        country = validated.pop("country", self._default_country)
        payload = self._client.get_json(
            self.base_url,
            {
                "engine": "google_news",
                "api_key": self._api_key,
                "q": query,
                "hl": language,
                "gl": country,
                "output": "json",
                **validated,
            },
            "SerpAPI",
        )
        provider_error = payload.get("error")
        if isinstance(provider_error, str) and provider_error:
            raise ProviderRequestError("SerpAPI", None, f"SerpAPI gagal: {provider_error}")
        return payload, limit
