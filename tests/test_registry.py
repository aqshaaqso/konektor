from social_connectors_api.endpoint_registry import ENDPOINT_REGISTRY
from social_connectors_api.request_models import build_request_model


def test_registry_contains_requested_platforms_and_all_endpoints() -> None:
    counts = {platform.id: len(platform.endpoints) for platform in ENDPOINT_REGISTRY.platforms}
    assert counts == {
        "tiktok": 20,
        "instagram": 11,
        "youtube": 13,
        "threads": 5,
        "news": 1,
    }
    assert ENDPOINT_REGISTRY.endpoint_count == 50


def test_every_endpoint_is_active_and_has_a_request_schema() -> None:
    for platform in ENDPOINT_REGISTRY.platforms:
        for endpoint in platform.endpoints:
            assert endpoint.status == "ACTIVE"
            assert endpoint.executable is True
            assert endpoint.path
            schema = build_request_model(endpoint).model_json_schema()
            required = set(schema.get("required", []))
            expected = {parameter.name for parameter in endpoint.parameters if parameter.required}
            assert required == expected
