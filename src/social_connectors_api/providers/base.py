"""Internal provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from social_connectors_api.models import SocialPost, SocialSearchRequest


@dataclass(frozen=True, slots=True)
class SocialSearchResult:
    items: list[SocialPost]
    next_cursor: str | None = None


class SocialProvider(Protocol):
    platform: str

    def search(self, request: SocialSearchRequest) -> SocialSearchResult: ...
