"""Generate exact Pydantic request models from endpoint definitions."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model

from .endpoint_registry import EndpointDefinition, ParameterDefinition


def _model_name(endpoint_id: str) -> str:
    return "".join(part.title() for part in re.split(r"[^a-zA-Z0-9]+", endpoint_id)) + "Request"


def _python_type(parameter: ParameterDefinition) -> type[Any]:
    if parameter.value_type == "boolean":
        return bool
    if parameter.value_type == "integer":
        return int
    return str


def _typed_default(parameter: ParameterDefinition) -> Any:
    value = parameter.default
    if parameter.value_type == "boolean" and isinstance(value, str):
        return value.lower() == "true"
    if parameter.value_type == "integer" and value not in (None, ""):
        return int(value)
    return value


def _example(parameter: ParameterDefinition) -> Any:
    if parameter.has_default:
        return _typed_default(parameter)
    placeholder = parameter.placeholder.strip()
    if parameter.value_type == "integer":
        match = re.search(r"-?\d+", placeholder)
        return int(match.group()) if match else max(1, int(parameter.minimum or 1))
    if parameter.value_type == "boolean":
        return False
    return placeholder or f"isi_{parameter.name}"


def build_request_model(endpoint: EndpointDefinition) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    example: dict[str, Any] = {}
    for parameter in endpoint.parameters:
        parameter_type = _python_type(parameter)
        annotation = parameter_type if parameter.required else parameter_type | None
        field_options: dict[str, Any] = {"description": parameter.description}
        if parameter.value_type == "integer":
            field_options.update(ge=parameter.minimum, le=parameter.maximum)
        elif parameter.value_type == "string":
            field_options.update(
                min_length=parameter.min_length,
                max_length=parameter.max_length,
            )
        if parameter.options:
            field_options["json_schema_extra"] = {"enum": list(parameter.options)}

        if parameter.required:
            field_info = Field(**field_options)
        else:
            default = _typed_default(parameter) if parameter.has_default else None
            field_info = Field(default=default, **field_options)
        fields[parameter.name] = (annotation, field_info)
        if parameter.required or parameter.has_default:
            example[parameter.name] = _example(parameter)

    config = ConfigDict(
        extra="forbid",
        title=f"{endpoint.label} request",
        json_schema_extra={"examples": [example]},
    )
    return create_model(_model_name(endpoint.id), __config__=config, **fields)
