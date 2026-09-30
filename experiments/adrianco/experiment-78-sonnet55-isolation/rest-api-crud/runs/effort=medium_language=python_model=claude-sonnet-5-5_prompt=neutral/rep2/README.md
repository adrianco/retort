# Book Collection API

Python standard library only (WSGI + `sqlite3`); no third-party runtime dependencies.

## Run
    python app.py            # PORT (default 8000), BOOKS_DB (default books.db)

## Test
    pip install pytest
    python -m pytest

## Endpoints
- `POST /books` — body `{title, author, year?, isbn?}`; 201 (title/author required, else 400)
- `GET /books` — list; optional `?author=` exact-match filter
- `GET /books/{id}` — 200 or 404
- `PUT /books/{id}` — full update; 200, 400, or 404
- `DELETE /books/{id}` — 204 or 404
- `GET /health` — `{"status": "ok"}`
