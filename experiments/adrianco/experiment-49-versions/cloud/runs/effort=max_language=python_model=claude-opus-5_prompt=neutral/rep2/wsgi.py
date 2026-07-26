"""WSGI entry point.

Examples:
    gunicorn wsgi:app
    waitress-serve --port 8000 wsgi:app
    flask --app wsgi run --port 8000
"""

from book_api import create_app

app = create_app()

if __name__ == "__main__":  # pragma: no cover
    app.run(host="127.0.0.1", port=8000)
