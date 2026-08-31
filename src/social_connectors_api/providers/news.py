"""Online-news connector backed by SerpAPI Google News."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from social_connectors_api.errors import ProviderRequestError
from social_connectors_api.http_client import JsonHttpClient, JsonHttpClientProtocol
from social_connectors_api.models import NewsArticle, NewsSearchRequest, NewsSource


class SerpApiNewsProvider:
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

    def search(self, request: NewsSearchRequest) -> list[NewsArticle]:
        payload = self._client.get_json(
            self.base_url,
            {
                "engine": "google_news",
                "api_key": self._api_key,
                "q": request.query,
                "hl": request.language or self._default_language,
                "gl": request.country or self._default_country,
                "output": "json",
            },
            "SerpAPI",
        )
        provider_error = payload.get("error")
        if isinstance(provider_error, str) and provider_error:
            raise ProviderRequestError("SerpAPI", None, f"SerpAPI gagal: {provider_error}")
        articles = [self._normalize(item) for item in self._flatten(payload)]
        normalized = [article for article in articles if article is not None]
        if request.sort.value == "date":
            normalized.sort(key=self._published_timestamp, reverse=True)
        return normalized[: request.limit]

    @staticmethod
    def _flatten(payload: dict[str, Any]) -> list[dict[str, Any]]:
        news_results = payload.get("news_results")
        if not isinstance(news_results, list):
            return []
        flattened: list[dict[str, Any]] = []
        for item in news_results:
            if not isinstance(item, dict):
                continue
            if item.get("title") and item.get("link"):
                flattened.append(item)
            highlight = item.get("highlight")
            if isinstance(highlight, dict):
                flattened.append(highlight)
            stories = item.get("stories")
            if isinstance(stories, list):
                flattened.extend(story for story in stories if isinstance(story, dict))
        return flattened

    @staticmethod
    def _normalize(item: dict[str, Any]) -> NewsArticle | None:
        title = str(item.get("title") or "").strip()
        url = str(item.get("link") or "").strip()
        if not title or not url:
            return None
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        authors = source.get("authors") if isinstance(source.get("authors"), list) else []
        return NewsArticle(
            external_id=sha256(f"{url}|{title}".encode()).hexdigest(),
            title=title,
            url=url,
            source=NewsSource(
                name=str(source.get("name") or "Unknown"),
                authors=[str(author) for author in authors],
                icon_url=str(source["icon"]) if source.get("icon") else None,
            ),
            published_at=str(item["iso_date"]) if item.get("iso_date") else None,
            published_text=str(item["date"]) if item.get("date") else None,
            image_url=str(item["thumbnail"]) if item.get("thumbnail") else None,
            collected_at=datetime.now(UTC),
        )

    @staticmethod
    def _published_timestamp(article: NewsArticle) -> float:
        if article.published_at is None:
            return float("-inf")
        try:
            return datetime.fromisoformat(article.published_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return float("-inf")
