"""Export the FastAPI schema to a committed OpenAPI JSON snapshot."""

from __future__ import annotations

import json
from pathlib import Path

from social_connectors_api.main import app


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "openapi" / "openapi.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI written to {output}")


if __name__ == "__main__":
    main()
