"""TikTok keyword connector backed by EnsembleData."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from social_connectors_api.models import SocialPost, SocialSearchRequest

from .base import SocialSearchResult
from .ensembledata import EnsembleDataClient


class TikTokProvider:
    platform = "tiktok"
    endpoint = "/tt/keyword/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30,
        client: EnsembleDataClient | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client or EnsembleDataClient(api_key, timeout_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))

    def search(self, request: SocialSearchRequest) -> SocialSearchResult:
        payload = self._client.get_json(
            self.endpoint,
            {
                "name": request.query,
                "cursor": request.cursor or "0",
                "period": self._period_for(request, self._clock().date()),
                "sorting": "0",
                "country": "id",
                "match_exactly": "false",
                "get_author_stats": "false",
            },
        )
        records = [
            record
            for record in self._to_records(payload)
            if record.published_at is not None
            and request.start_date <= record.published_at.date() <= request.end_date
        ]
        data = payload.get("data", {})
        next_cursor = data.get("nextCursor") if isinstance(data, dict) else None
        return SocialSearchResult(
            items=records[: request.limit],
            next_cursor=str(next_cursor) if next_cursor not in (None, "") else None,
        )

    @staticmethod
    def _period_for(request: SocialSearchRequest, today: date) -> str:
        if request.end_date < today:
            return "0"
        age_days = max(0, (today - request.start_date).days)
        for supported_days in (1, 7, 30, 90, 180):
            if age_days <= supported_days:
                return str(supported_days)
        return "0"

    @classmethod
    def _to_records(cls, payload: dict[str, Any]) -> list[SocialPost]:
        outer = payload.get("data", {})
        items = outer.get("data", []) if isinstance(outer, dict) else []
        if not isinstance(items, list):
            return []
        records: list[SocialPost] = []
        for item in items:
            info = item.get("aweme_info") if isinstance(item, dict) else None
            if not isinstance(info, dict):
                continue
            post_id = info.get("aweme_id") or item.get("provider_doc_id_str")
            published_at = cls._timestamp(info.get("create_time"))
            if not isinstance(post_id, (str, int)) or published_at is None:
                continue
            author = info.get("author", {})
            statistics = info.get("statistics", {})
            author = author if isinstance(author, dict) else {}
            statistics = statistics if isinstance(statistics, dict) else {}
            username = str(author.get("unique_id") or "").strip()
            post_id_text = str(post_id)
            url = (
                f"https://www.tiktok.com/@{username}/video/{post_id_text}"
                if username
                else f"https://www.tiktok.com/video/{post_id_text}"
            )
            records.append(
                SocialPost(
                    platform=cls.platform,
                    post_id=post_id_text,
                    text=str(info.get("desc") or "").strip(),
                    author=str(author.get("nickname") or username).strip(),
                    published_at=published_at,
                    url=url,
                    like_count=cls._integer(statistics.get("digg_count")),
                    comment_count=cls._integer(statistics.get("comment_count")),
                    share_count=cls._integer(statistics.get("share_count")),
                    view_count=cls._integer(statistics.get("play_count")),
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
