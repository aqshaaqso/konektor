"""Threads keyword connector backed by EnsembleData."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from social_connectors_api.models import SocialPost, SocialSearchRequest

from .base import SocialSearchResult
from .ensembledata import EnsembleDataClient


class ThreadsProvider:
    platform = "threads"
    endpoint = "/threads/keyword/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30,
        client: EnsembleDataClient | None = None,
    ) -> None:
        self._client = client or EnsembleDataClient(api_key, timeout_seconds)

    def search(self, request: SocialSearchRequest) -> SocialSearchResult:
        payload = self._client.get_json(
            self.endpoint,
            {"name": request.query, "sorting": "0"},
        )
        records = self._to_records(payload, request)
        return SocialSearchResult(items=records[: request.limit])

    @classmethod
    def _to_records(cls, payload: dict[str, Any], request: SocialSearchRequest) -> list[SocialPost]:
        entries = payload.get("data", [])
        if not isinstance(entries, list):
            return []
        records: list[SocialPost] = []
        for entry in entries:
            node = entry.get("node", {}) if isinstance(entry, dict) else {}
            thread = node.get("thread", {}) if isinstance(node, dict) else {}
            items = thread.get("thread_items", []) if isinstance(thread, dict) else []
            if not isinstance(items, list):
                continue
            for thread_item in items:
                post = thread_item.get("post") if isinstance(thread_item, dict) else None
                if not isinstance(post, dict):
                    continue
                published_at = cls._timestamp(post.get("taken_at"))
                post_id = post.get("id") or post.get("pk")
                if (
                    published_at is None
                    or post_id is None
                    or not request.start_date <= published_at.date() <= request.end_date
                ):
                    continue
                user = post.get("user", {})
                info = post.get("text_post_app_info", {})
                user = user if isinstance(user, dict) else {}
                info = info if isinstance(info, dict) else {}
                caption = post.get("caption", {})
                text = caption.get("text", "") if isinstance(caption, dict) else caption
                username = str(user.get("username") or "").strip()
                code = str(post.get("code") or "").strip()
                reposts = cls._integer(info.get("repost_count")) or 0
                quotes = cls._integer(info.get("quote_count")) or 0
                records.append(
                    SocialPost(
                        platform=cls.platform,
                        post_id=str(post_id),
                        text=str(text or "").strip(),
                        author=username,
                        published_at=published_at,
                        url=(
                            f"https://www.threads.net/@{username}/post/{code}"
                            if username and code
                            else "https://www.threads.net/"
                        ),
                        like_count=cls._integer(post.get("like_count")),
                        comment_count=cls._integer(info.get("direct_reply_count")),
                        share_count=reposts + quotes if reposts or quotes else None,
                    )
                )
        return records

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
