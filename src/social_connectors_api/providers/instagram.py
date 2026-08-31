"""Instagram search connector backed by EnsembleData."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from social_connectors_api.models import SocialPost, SocialSearchRequest

from .base import SocialSearchResult
from .ensembledata import EnsembleDataClient


class InstagramProvider:
    platform = "instagram"
    endpoint = "/instagram/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30,
        client: EnsembleDataClient | None = None,
    ) -> None:
        self._client = client or EnsembleDataClient(api_key, timeout_seconds)

    def search(self, request: SocialSearchRequest) -> SocialSearchResult:
        payload = self._client.get_json(self.endpoint, {"text": request.query})
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return SocialSearchResult(items=[])
        records = (
            self._content_records(data, request)
            + self._account_records(data)
            + self._topic_records(data)
        )
        return SocialSearchResult(items=records[: request.limit])

    @classmethod
    def _content_records(
        cls, data: dict[str, Any], request: SocialSearchRequest
    ) -> list[SocialPost]:
        candidates: list[Any] = []
        for key in ("posts", "media", "content", "items"):
            value = data.get(key)
            if isinstance(value, list):
                candidates.extend(value)
        records: list[SocialPost] = []
        for candidate in candidates:
            item = cls._unwrap(candidate)
            if not isinstance(item, dict):
                continue
            post_id = item.get("pk") or item.get("id")
            code = item.get("code") or item.get("shortcode")
            published_at = cls._timestamp(item.get("taken_at") or item.get("timestamp"))
            if (post_id is None and not code) or (
                published_at is not None
                and not request.start_date <= published_at.date() <= request.end_date
            ):
                continue
            user = item.get("user", {})
            user = user if isinstance(user, dict) else {}
            caption = item.get("caption")
            caption = caption.get("text") if isinstance(caption, dict) else caption
            username = str(user.get("username") or item.get("username") or "").strip()
            url = str(item.get("url") or "").strip()
            if not url and code:
                url = f"https://www.instagram.com/p/{code}/"
            records.append(
                SocialPost(
                    platform=cls.platform,
                    post_id=str(post_id or code),
                    text=str(caption or item.get("text") or "").strip(),
                    author=username,
                    published_at=published_at,
                    url=url or "https://www.instagram.com/",
                    like_count=cls._integer(item.get("like_count")),
                    comment_count=cls._integer(item.get("comment_count")),
                    view_count=cls._integer(item.get("view_count") or item.get("play_count")),
                )
            )
        return records

    @classmethod
    def _account_records(cls, data: dict[str, Any]) -> list[SocialPost]:
        users = data.get("users", [])
        if not isinstance(users, list):
            return []
        records: list[SocialPost] = []
        for entry in users:
            user = entry.get("user") if isinstance(entry, dict) else None
            if not isinstance(user, dict):
                continue
            username = str(user.get("username") or "").strip()
            identifier = user.get("pk") or user.get("id") or username
            if not username or not identifier:
                continue
            full_name = str(user.get("full_name") or "").strip()
            records.append(
                SocialPost(
                    platform=cls.platform,
                    post_id=f"account:{identifier}",
                    text=f"{full_name}\n@{username}".strip(),
                    author=username,
                    published_at=None,
                    url=f"https://www.instagram.com/{username}/",
                )
            )
        return records

    @classmethod
    def _topic_records(cls, data: dict[str, Any]) -> list[SocialPost]:
        records: list[SocialPost] = []
        hashtags = data.get("hashtags", [])
        if isinstance(hashtags, list):
            for entry in hashtags:
                hashtag = entry.get("hashtag") if isinstance(entry, dict) else None
                if not isinstance(hashtag, dict):
                    continue
                name = str(hashtag.get("name") or "").strip().lstrip("#")
                identifier = hashtag.get("id") or name
                if name and identifier:
                    records.append(
                        SocialPost(
                            platform=cls.platform,
                            post_id=f"topic:{identifier}",
                            text=f"#{name}",
                            author="Topik Instagram",
                            published_at=None,
                            url=f"https://www.instagram.com/explore/tags/{name}/",
                        )
                    )
        places = data.get("places", [])
        if isinstance(places, list):
            for entry in places:
                place = entry.get("place") if isinstance(entry, dict) else None
                if not isinstance(place, dict):
                    continue
                location = place.get("location", {})
                location = location if isinstance(location, dict) else {}
                identifier = location.get("pk") or location.get("facebook_places_id")
                title = str(place.get("title") or location.get("name") or "").strip()
                if title and identifier:
                    records.append(
                        SocialPost(
                            platform=cls.platform,
                            post_id=f"place:{identifier}",
                            text=title,
                            author="Lokasi Instagram",
                            published_at=None,
                            url=(f"https://www.instagram.com/explore/locations/{identifier}/"),
                        )
                    )
        return records

    @staticmethod
    def _unwrap(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for key in ("media", "post", "content", "item"):
            if isinstance(value.get(key), dict):
                return value[key]
        return value

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        try:
            return datetime.fromtimestamp(int(value), tz=UTC)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _integer(value: Any) -> int | None:
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
