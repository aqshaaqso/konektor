"""Typed access to the checked-in connector endpoint registry."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REGISTRY_FILE = Path(__file__).with_name("endpoint_registry.json")


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    name: str
    label: str
    type: str
    value_type: str
    required: bool
    allow_empty: bool
    description: str
    placeholder: str
    default: Any = None
    has_default: bool = False
    options: tuple[Any, ...] = ()
    minimum: int | float | None = None
    maximum: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ParameterDefinition:
        return cls(
            name=value["name"],
            label=value["label"],
            type=value["type"],
            value_type=value["value_type"],
            required=value["required"],
            allow_empty=value["allow_empty"],
            description=value["description"],
            placeholder=value["placeholder"],
            default=value.get("default"),
            has_default="default" in value,
            options=tuple(option["value"] for option in value.get("options", [])),
            minimum=value.get("minimum"),
            maximum=value.get("maximum"),
            min_length=value.get("min_length"),
            max_length=value.get("max_length"),
        )

    def coerce(self, value: Any) -> str:
        if value is None:
            raise ValueError(f"Parameter {self.label} wajib diisi")
        if self.value_type == "boolean":
            if isinstance(value, bool):
                return "true" if value else "false"
            normalized = str(value).strip().lower()
            if normalized not in {"true", "false"}:
                raise ValueError(f"Parameter {self.label} harus true atau false")
            return normalized

        text = str(value).strip()
        if not text and not self.allow_empty:
            raise ValueError(f"Parameter {self.label} wajib diisi")
        if self.value_type == "integer" and text:
            if not re.fullmatch(r"-?\d+", text):
                raise ValueError(f"Parameter {self.label} harus berupa angka bulat")
            number = int(text)
            if self.minimum is not None and number < self.minimum:
                raise ValueError(f"Parameter {self.label} minimal {self.minimum:g}")
            if self.maximum is not None and number > self.maximum:
                raise ValueError(f"Parameter {self.label} maksimal {self.maximum:g}")
            text = str(number)
        if self.min_length is not None and len(text) < self.min_length:
            raise ValueError(f"Parameter {self.label} minimal {self.min_length} karakter")
        if self.max_length is not None and len(text) > self.max_length:
            raise ValueError(f"Parameter {self.label} maksimal {self.max_length} karakter")
        if self.options and text not in {str(option) for option in self.options}:
            raise ValueError(f"Nilai parameter {self.label} tidak tersedia")
        if self.type == "url" and text:
            parsed = urlsplit(text)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"Parameter {self.label} harus berupa URL HTTP/HTTPS")
            hostname = parsed.hostname.lower()
            if hostname != "tiktok.com" and not hostname.endswith(".tiktok.com"):
                raise ValueError("URL TikTok harus berasal dari domain tiktok.com")
        return text


@dataclass(frozen=True, slots=True)
class EndpointDefinition:
    id: str
    label: str
    path: str
    method: str
    description: str
    parameters: tuple[ParameterDefinition, ...]
    pagination: tuple[str, ...]
    response_type: str
    status: str
    executable: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EndpointDefinition:
        return cls(
            id=value["id"],
            label=value["label"],
            path=value["path"],
            method=value["method"],
            description=value["description"],
            parameters=tuple(ParameterDefinition.from_dict(item) for item in value["parameters"]),
            pagination=tuple(value["pagination"]),
            response_type=value["response_type"],
            status=value["status"],
            executable=value["executable"],
        )

    def validate_parameters(self, supplied: dict[str, Any]) -> dict[str, str]:
        definitions = {parameter.name: parameter for parameter in self.parameters}
        unknown = sorted(set(supplied) - set(definitions))
        if unknown:
            raise ValueError(f"Parameter tidak dikenal: {', '.join(unknown)}")
        validated: dict[str, str] = {}
        for parameter in self.parameters:
            if parameter.name not in supplied:
                if parameter.required:
                    raise ValueError(f"Parameter {parameter.label} wajib diisi")
                continue
            value = supplied[parameter.name]
            if value in (None, "") and not parameter.required:
                continue
            validated[parameter.name] = parameter.coerce(value)
        return validated


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    id: str
    name: str
    endpoints: tuple[EndpointDefinition, ...]


class EndpointRegistry:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.source_url = payload["source_url"]
        self.generated_at = payload["generated_at"]
        self.source_sha256 = payload["source_sha256"]
        self.platforms = tuple(
            PlatformDefinition(
                id=platform["id"],
                name=platform["name"],
                endpoints=tuple(
                    EndpointDefinition.from_dict(endpoint) for endpoint in platform["endpoints"]
                ),
            )
            for platform in payload["platforms"]
        )
        self._payload = payload

    @classmethod
    def load(cls, path: Path = REGISTRY_FILE) -> EndpointRegistry:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def public_payload(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._payload))

    @property
    def endpoint_count(self) -> int:
        return sum(len(platform.endpoints) for platform in self.platforms)


ENDPOINT_REGISTRY = EndpointRegistry.load()
