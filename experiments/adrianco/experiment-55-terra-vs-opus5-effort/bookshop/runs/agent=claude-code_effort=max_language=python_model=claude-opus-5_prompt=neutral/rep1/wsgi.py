"""WSGI entry point.

    flask --app wsgi run          # development server
    gunicorn wsgi:app             # production-ish
    python wsgi.py                # development server, no flask CLI needed
"""

from __future__ import annotations

import os

from bookapi import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
