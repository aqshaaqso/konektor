"""Public request and response contracts exposed by Swagger."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _today() -> date:
    return date.today()


def _thirty_days_ago() -> date:
    return date.today() - timedelta(days=30)


class SocialSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Nusa Tenggara Timur",
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "limit": 20,
            }
        }
    )

    query: str = Field(min_length=1, max_length=200, description="Kata kunci pencarian")
    start_date: date = Field(default_factory=_thirty_days_ago)
    end_date: date = Field(default_factory=_today)
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=500)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query tidak boleh kosong")
        return normalized

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_date > self.end_date:
            raise ValueError("start_date tidak boleh melewati end_date")
        return self


class NewsSort(StrEnum):
    RELEVANCE = "relevance"
    DATE = "date"


class NewsSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "ekonomi Indonesia",
                "limit": 20,
                "language": "id",
                "country": "id",
                "sort": "date",
            }
        }
    )

    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=20, ge=1, le=100)
    language: str | None = Field(default=None, min_length=2, max_length=10)
    country: str | None = Field(default=None, min_length=2, max_length=10)
    sort: NewsSort = NewsSort.RELEVANCE

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query tidak boleh kosong")
        return normalized


class SocialPost(BaseModel):
    platform: str
    post_id: str
    text: str
    author: str
    published_at: datetime | None = None
    url: str
    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    view_count: int | None = None


class SocialSearchResponse(BaseModel):
    platform: str
    provider: str = "ensembledata"
    count: int
    next_cursor: str | None = None
    items: list[SocialPost]


class NewsSource(BaseModel):
    name: str
    authors: list[str] = Field(default_factory=list)
    icon_url: str | None = None


class NewsArticle(BaseModel):
    external_id: str
    title: str
    url: str
    source: NewsSource
    published_at: str | None = None
    published_text: str | None = None
    image_url: str | None = None
    collected_at: datetime


class NewsSearchResponse(BaseModel):
    platform: str = "online_news"
    provider: str = "serpapi_google_news"
    count: int
    items: list[NewsArticle]


class ConnectorStatus(BaseModel):
    name: str
    configured: bool
    endpoint_count: int


class HealthResponse(BaseModel):
    status: str
    connectors: list[ConnectorStatus]


class ApiError(BaseModel):
    error: str
    detail: str
    connector: str | None = None
    provider: str | None = None


class EndpointExecutionResponse(BaseModel):
    platform: str
    endpoint_id: str
    endpoint_label: str
    provider: str
    upstream_path: str
    response_type: str
    result_count: int
    next_cursor: str | None = None
    units_charged: int | None = None
    columns: list[str]
    rows: list[dict[str, Any]]
    raw: dict[str, Any]


JsonObject = dict[str, Any]
