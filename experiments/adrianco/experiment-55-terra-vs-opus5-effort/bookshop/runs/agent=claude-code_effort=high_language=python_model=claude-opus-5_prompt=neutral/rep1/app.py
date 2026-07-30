"""Entry point: ``python app.py`` or ``flask --app app run``."""

from __future__ import annotations

import os

from bookapi import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
