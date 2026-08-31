"""Generate a Postman collection that mirrors every Swagger operation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from social_connectors_api.endpoint_registry import ENDPOINT_REGISTRY, ParameterDefinition

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "postman" / "Social Connectors API.postman_collection.json"


def _test_event() -> list[dict[str, Any]]:
    return [
        {
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": ["pm.test('Status 200', () => pm.response.to.have.status(200));"],
            },
        }
    ]


def _request_item(
    name: str,
    method: str,
    path: str,
    description: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = [{"key": "Accept", "value": "application/json"}]
    request: dict[str, Any] = {
        "method": method,
        "header": headers,
        "url": {
            "raw": f"{{{{baseUrl}}}}{path}",
            "host": ["{{baseUrl}}"],
            "path": path.strip("/").split("/"),
        },
        "description": description,
    }
    if body is not None:
        headers.insert(0, {"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, ensure_ascii=False, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    return {"name": name, "request": request, "event": _test_event()}


def _example(parameter: ParameterDefinition) -> Any:
    if parameter.has_default:
        value = parameter.default
    else:
        value = parameter.placeholder.strip()
    if parameter.value_type == "boolean":
        return value if isinstance(value, bool) else str(value).lower() == "true"
    if parameter.value_type == "integer":
        match = re.search(r"-?\d+", str(value))
        return int(match.group()) if match else max(1, int(parameter.minimum or 1))
    return value or f"replace_{parameter.name}"


def _catalog_folders() -> list[dict[str, Any]]:
    folders: list[dict[str, Any]] = []
    for platform in ENDPOINT_REGISTRY.platforms:
        items: list[dict[str, Any]] = []
        for endpoint in platform.endpoints:
            body = {
                parameter.name: _example(parameter)
                for parameter in endpoint.parameters
                if parameter.required or parameter.has_default
            }
            items.append(
                _request_item(
                    endpoint.label,
                    "POST",
                    f"/v1/connectors/{platform.id}/{endpoint.id}",
                    (
                        f"{endpoint.description}\n\n"
                        f"Upstream provider: {endpoint.method} {endpoint.path}. "
                        "Ganti nilai contoh sebelum menjalankan request."
                    ),
                    body,
                )
            )
        folders.append({"name": platform.name, "item": items})
    return folders


def main() -> None:
    social_body = {
        "query": "{{searchQuery}}",
        "start_date": "{{startDate}}",
        "end_date": "{{endDate}}",
        "limit": 20,
    }
    collection = {
        "info": {
            "_postman_id": "15f96d20-7bee-4d15-887d-32df368bdb31",
            "name": "Social Connectors API - Complete",
            "description": (
                "50 endpoint provider lengkap dan 5 convenience search endpoint. "
                "Credential disimpan di server, bukan di collection."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "event": [
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "const end = new Date();",
                        "const start = new Date(end);",
                        "start.setUTCDate(start.getUTCDate() - 30);",
                        (
                            "pm.collectionVariables.set('startDate', "
                            "start.toISOString().slice(0, 10));"
                        ),
                        "pm.collectionVariables.set('endDate', end.toISOString().slice(0, 10));",
                    ],
                },
            }
        ],
        "variable": [
            {"key": "baseUrl", "value": "http://127.0.0.1:8000", "type": "string"},
            {"key": "searchQuery", "value": "Nusa Tenggara Timur", "type": "string"},
            {"key": "startDate", "value": "", "type": "string"},
            {"key": "endDate", "value": "", "type": "string"},
        ],
        "item": [
            {
                "name": "System",
                "item": [
                    _request_item("Health", "GET", "/health", "Status API dan connector."),
                    _request_item(
                        "Endpoint Catalog",
                        "GET",
                        "/v1/catalog",
                        "Daftar metadata 50 endpoint provider.",
                    ),
                ],
            },
            {
                "name": "Convenience Searches",
                "item": [
                    _request_item(
                        f"Search {platform.title()}",
                        "POST",
                        f"/v1/{platform}/search",
                        "Pencarian ringkas dengan output sosial yang dinormalisasi.",
                        social_body,
                    )
                    for platform in ("youtube", "instagram", "tiktok", "threads")
                ]
                + [
                    _request_item(
                        "Search Online News",
                        "POST",
                        "/v1/news/search",
                        "Pencarian ringkas Google News melalui SerpAPI.",
                        {
                            "query": "{{searchQuery}}",
                            "limit": 20,
                            "language": "id",
                            "country": "id",
                            "sort": "date",
                        },
                    )
                ],
            },
            {"name": "Complete Connector Catalog", "item": _catalog_folders()},
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Postman collection written with {ENDPOINT_REGISTRY.endpoint_count} catalog requests")


if __name__ == "__main__":
    main()
