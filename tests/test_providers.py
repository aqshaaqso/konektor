from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from social_connectors_api.models import NewsSearchRequest, SocialSearchRequest
from social_connectors_api.providers.news import SerpApiNewsProvider
from social_connectors_api.providers.tiktok import TikTokProvider


class EnsembleStub:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.endpoint = ""
        self.params: dict[str, str] = {}

    def get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        self.endpoint = endpoint
        self.params = params
        return self.payload


class HttpStub:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.params: dict[str, str] = {}

    def get_json(self, _url: str, params: dict[str, str], _provider: str) -> dict[str, Any]:
        self.params = params
        return self.payload


def test_tiktok_connector_normalizes_response_and_cursor() -> None:
    client = EnsembleStub(
        {
            "data": {
                "nextCursor": "next-page",
                "data": [
                    {
                        "aweme_info": {
                            "aweme_id": "123",
                            "create_time": 1788134400,
                            "desc": "Contoh video",
                            "author": {"unique_id": "akun", "nickname": "Akun"},
                            "statistics": {"digg_count": 12, "play_count": 100},
                        }
                    }
                ],
            }
        }
    )
    provider = TikTokProvider(
        "not-used",
        client=client,
        clock=lambda: datetime(2026, 8, 31, tzinfo=UTC),
    )
    result = provider.search(
        SocialSearchRequest(
            query="NTT",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            limit=5,
        )
    )
    assert client.endpoint == "/tt/keyword/search"
    assert result.next_cursor == "next-page"
    assert result.items[0].post_id == "123"
    assert result.items[0].view_count == 100


def test_serpapi_connector_normalizes_google_news() -> None:
    client = HttpStub(
        {
            "news_results": [
                {
                    "title": "Berita contoh",
                    "link": "https://example.com/news",
                    "iso_date": "2026-08-31T08:00:00Z",
                    "source": {"name": "Example Media", "authors": ["Reporter"]},
                }
            ]
        }
    )
    provider = SerpApiNewsProvider("secret", client=client)
    result = provider.search(NewsSearchRequest(query="ekonomi", limit=5))
    assert client.params["engine"] == "google_news"
    assert result[0].title == "Berita contoh"
    assert result[0].source.name == "Example Media"
    assert result[0].external_id
