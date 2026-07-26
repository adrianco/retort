"""Development entry point.

Run directly::

    python app.py

or through the Flask CLI, which discovers the ``create_app`` factory::

    flask --app bookapi run --port 8000
"""

from __future__ import annotations

import os

from bookapi import create_app

app = create_app()


if __name__ == "__main__":
    # Port 8000 rather than Flask's default 5000, which macOS uses for AirPlay.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
