"""Import only the supported platform definitions from an EnsembleData registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PLATFORMS = ("tiktok", "instagram", "youtube", "threads", "news")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    PROJECT_ROOT.parent
    / "social-media-api-testing"
    / "src"
    / "social_media_api_testing"
    / "endpoint_registry.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "src" / "social_connectors_api" / "endpoint_registry.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = json.loads(args.source.read_text(encoding="utf-8"))
    selected = [platform for platform in payload["platforms"] if platform["id"] in PLATFORMS]
    found = {platform["id"] for platform in selected}
    missing = set(PLATFORMS) - found
    if missing:
        raise ValueError(f"Platform tidak ditemukan: {', '.join(sorted(missing))}")

    output = {
        "source_url": payload["source_url"],
        "generated_at": payload["generated_at"],
        "source_sha256": payload["source_sha256"],
        "platforms": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    endpoint_count = sum(len(platform["endpoints"]) for platform in selected)
    print(f"Imported {endpoint_count} endpoints to {args.output}")


if __name__ == "__main__":
    main()
