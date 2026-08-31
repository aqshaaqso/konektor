"""Register every catalog endpoint as an explicit Swagger operation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .dependencies import SettingsDep
from .endpoint_registry import ENDPOINT_REGISTRY, EndpointDefinition, PlatformDefinition
from .models import ApiError, EndpointExecutionResponse
from .normalizer import ResponseNormalizer
from .providers.catalog import EnsembleDataCatalogProvider, SerpApiCatalogProvider
from .request_models import build_request_model

PROVIDER_RESPONSES = {
    429: {"model": ApiError, "description": "Kuota provider sedang tercapai"},
    502: {"model": ApiError, "description": "Provider menolak atau gagal memproses request"},
    503: {"model": ApiError, "description": "Credential connector belum dikonfigurasi"},
}


def _sanitize(value: Any) -> Any:
    secret_keys = {"token", "api_key", "apikey", "authorization"}
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in secret_keys else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _execute(
    platform: PlatformDefinition,
    endpoint: EndpointDefinition,
    parameters: dict[str, Any],
    settings: SettingsDep,
) -> EndpointExecutionResponse:
    try:
        if platform.id == "news":
            raw, row_limit = SerpApiCatalogProvider(
                settings.require_serpapi_key(),
                settings.http_timeout_seconds,
                settings.news_default_language,
                settings.news_default_country,
            ).execute(endpoint, parameters)
            provider_name = "serpapi_google_news"
        else:
            raw = EnsembleDataCatalogProvider(
                settings.require_ensembledata_key(), settings.http_timeout_seconds
            ).execute(endpoint, parameters)
            row_limit = 100
            provider_name = "ensembledata"
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    normalized = ResponseNormalizer().normalize(raw, endpoint.response_type, row_limit)
    return EndpointExecutionResponse(
        platform=platform.id,
        endpoint_id=endpoint.id,
        endpoint_label=endpoint.label,
        provider=provider_name,
        upstream_path=endpoint.path,
        response_type=normalized.response_type,
        result_count=len(normalized.rows),
        next_cursor=normalized.next_cursor,
        units_charged=normalized.units_charged,
        columns=normalized.columns,
        rows=normalized.rows,
        raw=_sanitize(raw),
    )


def _handler_factory(
    platform: PlatformDefinition,
    endpoint: EndpointDefinition,
    request_model: type[BaseModel],
):
    def execute_endpoint(body: BaseModel, settings: SettingsDep) -> EndpointExecutionResponse:
        return _execute(
            platform,
            endpoint,
            body.model_dump(exclude_none=True),
            settings,
        )

    execute_endpoint.__name__ = f"execute_{endpoint.id}"
    execute_endpoint.__annotations__["body"] = request_model
    return execute_endpoint


def register_catalog_routes(router: APIRouter) -> None:
    for platform in ENDPOINT_REGISTRY.platforms:
        tag = "Online News" if platform.id == "news" else platform.name
        for endpoint in platform.endpoints:
            request_model = build_request_model(endpoint)
            handler = _handler_factory(platform, endpoint, request_model)
            router.add_api_route(
                f"/connectors/{platform.id}/{endpoint.id}",
                handler,
                methods=["POST"],
                response_model=EndpointExecutionResponse,
                tags=[tag],
                summary=endpoint.label,
                description=(
                    f"{endpoint.description}\n\nUpstream: `{endpoint.method} {endpoint.path}`"
                ),
                response_description="Respons provider dalam bentuk normalized rows dan raw JSON",
                responses=PROVIDER_RESPONSES,
                operation_id=f"execute_{endpoint.id}",
            )
