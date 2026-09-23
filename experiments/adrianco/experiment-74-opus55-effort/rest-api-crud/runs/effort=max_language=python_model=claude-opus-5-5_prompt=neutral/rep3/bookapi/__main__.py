"""Serve the API with Flask's built-in server: ``python -m bookapi``.

Listens on ``$HOST:$PORT`` (default 127.0.0.1:8000). Port 8000 rather than
Flask's usual 5000, which macOS reserves for AirPlay Receiver.
"""

import os

from . import create_app


def main() -> None:
    app = create_app()
    # Empty variables count as unset.
    app.run(host=os.environ.get("HOST") or "127.0.0.1", port=int(os.environ.get("PORT") or 8000))


if __name__ == "__main__":
    main()
