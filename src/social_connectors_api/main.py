"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .errors import ConnectorNotConfiguredError, ProviderRequestError
from .routes import health_router, router

tags_metadata = [
    {"name": "System", "description": "Status service dan konfigurasi connector."},
    {"name": "YouTube", "description": "Pencarian YouTube melalui EnsembleData."},
    {"name": "Instagram", "description": "Pencarian Instagram melalui EnsembleData."},
    {"name": "TikTok", "description": "Pencarian TikTok melalui EnsembleData."},
    {"name": "Threads", "description": "Pencarian Threads melalui EnsembleData."},
    {"name": "Online News", "description": "Pencarian berita melalui SerpAPI Google News."},
]

app = FastAPI(
    title="Social Connectors API",
    summary="Connector sosial media dan berita online dalam satu API.",
    description=(
        "API mandiri untuk mencari konten publik YouTube, Instagram, TikTok, Threads, "
        "dan Google News. Credential provider hanya dibaca dari environment server."
    ),
    version=__version__,
    openapi_tags=tags_metadata,
    contact={"name": "API Maintainer"},
    license_info={"name": "Proprietary"},
)


@app.exception_handler(ConnectorNotConfiguredError)
def handle_missing_connector(_request: Request, error: ConnectorNotConfiguredError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "connector_not_configured",
            "connector": error.connector,
            "detail": str(error),
        },
    )


@app.exception_handler(ProviderRequestError)
def handle_provider_error(_request: Request, error: ProviderRequestError) -> JSONResponse:
    status_code = 429 if error.status_code == 429 else 502
    return JSONResponse(
        status_code=status_code,
        content={
            "error": "provider_request_failed",
            "provider": error.provider,
            "detail": error.message,
        },
    )


@app.get("/", tags=["System"], include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "Social Connectors API",
        "version": __version__,
        "swagger": "/docs",
        "openapi": "/openapi.json",
    }


app.include_router(health_router)
app.include_router(router)
