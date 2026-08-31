"""Normalize heterogeneous provider responses without discarding the raw payload."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

Scalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class NormalizedResponse:
    response_type: str
    columns: list[str]
    rows: list[dict[str, Scalar]]
    next_cursor: str | None
    units_charged: int | None


class ResponseNormalizer:
    list_keys = (
        "articles",
        "news_results",
        "posts",
        "comments",
        "replies",
        "videos",
        "shorts",
        "streams",
        "users",
        "followers",
        "followings",
        "reels",
        "results",
        "items",
        "data",
    )
    cursor_keys = (
        "nextCursor",
        "next_cursor",
        "last_cursor",
        "nextPageToken",
        "next_page_token",
    )
    units_keys = ("units_charged", "unitsCharged")

    def normalize(
        self, payload: dict[str, Any], expected_type: str, row_limit: int = 100
    ) -> NormalizedResponse:
        candidate = self._find_list(payload) if expected_type == "list" else None
        if candidate is not None:
            rows = [self._flatten_row(item) for item in candidate[:row_limit]]
            rows = [row for row in rows if row]
            response_type = "list"
        else:
            data = payload.get("data", payload)
            source = data if isinstance(data, dict) else {"value": data}
            flattened = self._flatten_mapping(source)
            rows = [{"field": key, "value": value} for key, value in flattened.items()]
            response_type = "object"
        return NormalizedResponse(
            response_type=response_type,
            columns=self._columns(rows),
            rows=rows,
            next_cursor=self._find_metadata(payload, self.cursor_keys),
            units_charged=self._find_integer_metadata(payload, self.units_keys),
        )

    def _find_list(self, value: Any, depth: int = 0) -> list[Any] | None:
        if depth > 6:
            return None
        if isinstance(value, list):
            return value
        if not isinstance(value, dict):
            return None
        for key in self.list_keys:
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
        for nested in value.values():
            candidate = self._find_list(nested, depth + 1)
            if candidate is not None:
                return candidate
        return None

    def _flatten_row(self, value: Any) -> dict[str, Scalar]:
        if isinstance(value, dict):
            return self._flatten_mapping(value)
        return {"value": self._scalar(value)}

    def _flatten_mapping(
        self, value: dict[str, Any], prefix: str = "", depth: int = 0
    ) -> dict[str, Scalar]:
        flattened: dict[str, Scalar] = {}
        for key, item in value.items():
            if len(flattened) >= 30:
                break
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, dict) and depth < 2:
                flattened.update(self._flatten_mapping(item, path, depth + 1))
            elif isinstance(item, (dict, list)):
                flattened[path] = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            else:
                flattened[path] = self._scalar(item)
        return flattened

    @staticmethod
    def _scalar(value: Any) -> Scalar:
        return value if value is None or isinstance(value, (str, int, float, bool)) else str(value)

    @staticmethod
    def _columns(rows: list[dict[str, Scalar]]) -> list[str]:
        return list(dict.fromkeys(key for row in rows for key in row))

    def _find_metadata(self, value: Any, keys: tuple[str, ...], depth: int = 0) -> str | None:
        if depth > 5 or not isinstance(value, dict):
            return None
        for key in keys:
            candidate = value.get(key)
            if candidate not in (None, ""):
                return str(candidate)
        for nested in value.values():
            result = self._find_metadata(nested, keys, depth + 1)
            if result is not None:
                return result
        return None

    def _find_integer_metadata(
        self, value: Any, keys: tuple[str, ...], depth: int = 0
    ) -> int | None:
        result = self._find_metadata(value, keys, depth)
        try:
            return int(result) if result is not None else None
        except (TypeError, ValueError):
            return None
