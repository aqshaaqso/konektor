"""HTTP endpoints for all connector searches."""

from __future__ import annotations

from fastapi import APIRouter

from .catalog_routes import register_catalog_routes
from .dependencies import SettingsDep
from .endpoint_registry import ENDPOINT_REGISTRY
from .models import (
    ApiError,
    HealthResponse,
    NewsSearchRequest,
    NewsSearchResponse,
    SocialSearchRequest,
    SocialSearchResponse,
)
from .providers import (
    InstagramProvider,
    SerpApiNewsProvider,
    ThreadsProvider,
    TikTokProvider,
    YouTubeProvider,
)
from .providers.base import SocialProvider

router = APIRouter(prefix="/v1")

PROVIDER_RESPONSES = {
    429: {"model": ApiError, "description": "Kuota provider sedang tercapai"},
    502: {"model": ApiError, "description": "Provider menolak atau gagal memproses request"},
    503: {"model": ApiError, "description": "Credential connector belum dikonfigurasi"},
}


def _social_response(provider: SocialProvider, body: SocialSearchRequest) -> SocialSearchResponse:
    result = provider.search(body)
    return SocialSearchResponse(
        platform=provider.platform,
        count=len(result.items),
        next_cursor=result.next_cursor,
        items=result.items,
    )


@router.post(
    "/youtube/search",
    tags=["YouTube"],
    summary="Cari video YouTube",
    response_description="Video YouTube yang sudah dinormalisasi",
    responses=PROVIDER_RESPONSES,
)
def search_youtube(body: SocialSearchRequest, settings: SettingsDep) -> SocialSearchResponse:
    provider = YouTubeProvider(settings.require_ensembledata_key(), settings.http_timeout_seconds)
    return _social_response(provider, body)


@router.post(
    "/instagram/search",
    tags=["Instagram"],
    summary="Cari konten Instagram",
    response_description="Konten Instagram yang sudah dinormalisasi",
    responses=PROVIDER_RESPONSES,
)
def search_instagram(body: SocialSearchRequest, settings: SettingsDep) -> SocialSearchResponse:
    provider = InstagramProvider(settings.require_ensembledata_key(), settings.http_timeout_seconds)
    return _social_response(provider, body)


@router.post(
    "/tiktok/search",
    tags=["TikTok"],
    summary="Cari video TikTok",
    response_description="Video TikTok yang sudah dinormalisasi",
    responses=PROVIDER_RESPONSES,
)
def search_tiktok(body: SocialSearchRequest, settings: SettingsDep) -> SocialSearchResponse:
    provider = TikTokProvider(settings.require_ensembledata_key(), settings.http_timeout_seconds)
    return _social_response(provider, body)


@router.post(
    "/threads/search",
    tags=["Threads"],
    summary="Cari post Threads",
    response_description="Post Threads yang sudah dinormalisasi",
    responses=PROVIDER_RESPONSES,
)
def search_threads(body: SocialSearchRequest, settings: SettingsDep) -> SocialSearchResponse:
    provider = ThreadsProvider(settings.require_ensembledata_key(), settings.http_timeout_seconds)
    return _social_response(provider, body)


@router.post(
    "/news/search",
    tags=["Online News"],
    summary="Cari berita online",
    response_description="Artikel Google News yang sudah dinormalisasi",
    responses=PROVIDER_RESPONSES,
)
def search_news(body: NewsSearchRequest, settings: SettingsDep) -> NewsSearchResponse:
    provider = SerpApiNewsProvider(
        settings.require_serpapi_key(),
        settings.http_timeout_seconds,
        settings.news_default_language,
        settings.news_default_country,
    )
    items = provider.search(body)
    return NewsSearchResponse(count=len(items), items=items)


@router.get(
    "/catalog",
    tags=["System"],
    summary="Daftar lengkap endpoint connector",
    response_description="Metadata 50 endpoint yang tersedia",
)
def get_catalog() -> dict[str, object]:
    return ENDPOINT_REGISTRY.public_payload()


register_catalog_routes(router)


health_router = APIRouter(tags=["System"])


@health_router.get("/health", summary="Periksa status API dan connector")
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        connectors=[
            {
                "name": "youtube",
                "configured": settings.ensembledata_api_key is not None,
                "endpoint_count": 13,
            },
            {
                "name": "instagram",
                "configured": settings.ensembledata_api_key is not None,
                "endpoint_count": 11,
            },
            {
                "name": "tiktok",
                "configured": settings.ensembledata_api_key is not None,
                "endpoint_count": 20,
            },
            {
                "name": "threads",
                "configured": settings.ensembledata_api_key is not None,
                "endpoint_count": 5,
            },
            {
                "name": "online_news",
                "configured": settings.serpapi_api_key is not None,
                "endpoint_count": 1,
            },
        ],
    )
