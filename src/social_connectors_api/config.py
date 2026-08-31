"""Environment-based runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

from .errors import ConnectorNotConfiguredError


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} harus berupa angka positif") from exc
    if value <= 0:
        raise ValueError(f"{name} harus lebih besar dari 0")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    ensembledata_api_key: str | None = field(repr=False)
    serpapi_api_key: str | None = field(repr=False)
    http_timeout_seconds: float
    news_default_language: str
    news_default_country: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        return cls(
            ensembledata_api_key=os.getenv("ENSEMBLEDATA_API_KEY") or None,
            serpapi_api_key=os.getenv("SERPAPI_API_KEY") or None,
            http_timeout_seconds=_positive_float("HTTP_TIMEOUT_SECONDS", 30),
            news_default_language=os.getenv("NEWS_DEFAULT_LANGUAGE", "id").strip() or "id",
            news_default_country=os.getenv("NEWS_DEFAULT_COUNTRY", "id").strip() or "id",
        )

    def require_ensembledata_key(self) -> str:
        if self.ensembledata_api_key is None:
            raise ConnectorNotConfiguredError("ensembledata")
        return self.ensembledata_api_key

    def require_serpapi_key(self) -> str:
        if self.serpapi_api_key is None:
            raise ConnectorNotConfiguredError("serpapi")
        return self.serpapi_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
