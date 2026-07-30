"""Entry point for running the Book Collection API.

Development::

    python app.py                 # http://127.0.0.1:8000

Production-ish (any WSGI server works, the module-level ``app`` is the target)::

    gunicorn 'app:app' --bind 0.0.0.0:8000
"""

from __future__ import annotations

import os

from bookapi import create_app

app = create_app()


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("DEBUG", "").lower() in {"1", "true", "yes"}
    app.logger.info("Serving %s on http://%s:%d", app.config["DATABASE"], host, port)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
