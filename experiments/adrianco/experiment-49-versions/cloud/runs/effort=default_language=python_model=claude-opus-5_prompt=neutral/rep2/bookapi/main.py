"""ASGI entry point.

    uvicorn bookapi.main:app --reload
    python -m bookapi.main
"""

from __future__ import annotations

import os

from bookapi.app import create_app

app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "bookapi.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )


if __name__ == "__main__":
    main()
