"""YouTube keyword connector backed by EnsembleData."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from social_connectors_api.models import SocialPost, SocialSearchRequest

from .base import SocialSearchResult
from .ensembledata import EnsembleDataClient


class YouTubeProvider:
    platform = "youtube"
    endpoint = "/youtube/search"

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
        reference_time = self._clock()
        payload = self._client.get_json(
            self.endpoint,
            {
                "keyword": request.query,
                "depth": str(max(1, math.ceil(request.limit / 20))),
                "start_cursor": request.cursor or "",
                "period": self._period_for(request, reference_time.date()),
                "sorting": "relevance",
                "get_additional_info": "false",
            },
        )
        records = [
            record
            for record in self._to_records(payload, reference_time)
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
            return "overall"
        age_days = max(0, (today - request.start_date).days)
        if age_days <= 1:
            return "today"
        if age_days <= 7:
            return "week"
        if age_days <= 31:
            return "month"
        if age_days <= 366:
            return "year"
        return "overall"

    @classmethod
    def _to_records(cls, payload: dict[str, Any], now: datetime) -> list[SocialPost]:
        data = payload.get("data", {})
        posts = data.get("posts", []) if isinstance(data, dict) else []
        if not isinstance(posts, list):
            return []
        records: list[SocialPost] = []
        for post in posts:
            renderer = post.get("videoRenderer") if isinstance(post, dict) else None
            if not isinstance(renderer, dict):
                continue
            video_id = renderer.get("videoId")
            published_at = cls._relative_time(
                cls._nested(renderer, "publishedTimeText", "simpleText"), now
            )
            if not isinstance(video_id, str) or not video_id or published_at is None:
                continue
            title = cls._run_text(renderer.get("title"))
            description = cls._snippet(renderer.get("detailedMetadataSnippets"))
            records.append(
                SocialPost(
                    platform=cls.platform,
                    post_id=video_id,
                    text=f"{title}\n{description}".strip(),
                    author=cls._run_text(renderer.get("longBylineText")),
                    published_at=published_at,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    view_count=cls._count(cls._nested(renderer, "viewCountText", "simpleText")),
                )
            )
        return records

    @staticmethod
    def _nested(value: Any, *keys: str) -> str:
        current = value
        for key in keys:
            if not isinstance(current, dict):
                return ""
            current = current.get(key)
        return current if isinstance(current, str) else ""

    @staticmethod
    def _run_text(value: Any) -> str:
        runs = value.get("runs", []) if isinstance(value, dict) else []
        if not isinstance(runs, list):
            return ""
        return "".join(
            run.get("text", "")
            for run in runs
            if isinstance(run, dict) and isinstance(run.get("text"), str)
        ).strip()

    @classmethod
    def _snippet(cls, value: Any) -> str:
        if not isinstance(value, list) or not value or not isinstance(value[0], dict):
            return ""
        return cls._run_text(value[0].get("snippetText"))

    @staticmethod
    def _relative_time(value: str, now: datetime) -> datetime | None:
        normalized = value.lower().replace("streamed", "").replace("premiered", "").strip()
        if normalized in {"today", "just now"}:
            return now
        if normalized == "yesterday":
            return now - timedelta(days=1)
        match = re.search(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", normalized)
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "minute":
            return now - timedelta(minutes=amount)
        if unit == "hour":
            return now - timedelta(hours=amount)
        return now - timedelta(days=amount * {"day": 1, "week": 7, "month": 30, "year": 365}[unit])

    @staticmethod
    def _count(value: str) -> int | None:
        match = re.search(r"([\d,.]+)\s*([kmb])?", value.lower())
        if not match:
            return None
        number, suffix = match.groups()
        if suffix:
            multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
            return int(float(number.replace(",", "")) * multipliers[suffix])
        digits = re.sub(r"\D", "", number)
        return int(digits) if digits else None
