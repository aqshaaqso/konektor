from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from social_connectors_api.config import Settings, get_settings
from social_connectors_api.main import app


def settings_without_credentials() -> Settings:
    return Settings(
        ensembledata_api_key=None,
        serpapi_api_key=None,
        http_timeout_seconds=1,
        news_default_language="id",
        news_default_country="id",
    )


def test_openapi_contains_all_connectors() -> None:
    schema = app.openapi()
    expected_paths = {
        "/health",
        "/v1/youtube/search",
        "/v1/instagram/search",
        "/v1/tiktok/search",
        "/v1/threads/search",
        "/v1/news/search",
        "/v1/catalog",
    }
    assert expected_paths <= set(schema["paths"])
    catalog_paths = [path for path in schema["paths"] if path.startswith("/v1/connectors/")]
    assert len(catalog_paths) == 50


def test_health_does_not_expose_secret_values() -> None:
    app.dependency_overrides[get_settings] = settings_without_credentials
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert all(not connector["configured"] for connector in response.json()["connectors"])
    assert "api_key" not in response.text.lower()


def test_missing_provider_credential_returns_503() -> None:
    app.dependency_overrides[get_settings] = settings_without_credentials
    try:
        response = TestClient(app).post(
            "/v1/youtube/search",
            json={
                "query": "NTT",
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "limit": 5,
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["connector"] == "ensembledata"


def _postman_requests(items: list[dict[str, object]]):
    for item in items:
        if "request" in item:
            yield item
        else:
            yield from _postman_requests(item.get("item", []))


def test_postman_paths_match_openapi() -> None:
    project_root = Path(__file__).resolve().parents[1]
    collection_path = project_root / "postman" / "Social Connectors API.postman_collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    schema_paths = set(app.openapi()["paths"])

    postman_paths = {
        "/" + "/".join(item["request"]["url"]["path"])
        for item in _postman_requests(collection["item"])
    }
    assert postman_paths == schema_paths


def test_postman_contains_all_catalog_requests() -> None:
    project_root = Path(__file__).resolve().parents[1]
    collection_path = project_root / "postman" / "Social Connectors API.postman_collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    paths = [
        "/" + "/".join(item["request"]["url"]["path"])
        for item in _postman_requests(collection["item"])
    ]
    assert sum(path.startswith("/v1/connectors/") for path in paths) == 50
