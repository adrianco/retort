"""WSGI entry point: ``python wsgi.py`` or ``flask --app wsgi run``."""

import os

from bookapi import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
