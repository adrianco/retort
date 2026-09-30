# Book Collection API

Python 3 REST API using only the standard library (WSGI + SQLite). No dependencies to run.

## Run
    python app.py            # http://127.0.0.1:8000  (env: PORT, BOOKS_DB=books.db)

## Test
    pip install pytest
    python -m pytest tests

## Endpoints
- `POST /books` — body `{title, author, year, isbn}`; title and author required → 201
- `GET /books` — list; optional `?author=Name` exact-match filter
- `GET /books/{id}` — 200 or 404
- `PUT /books/{id}` — full update; 200, 400, or 404
- `DELETE /books/{id}` — 204 or 404
- `GET /health` — `{"status": "ok"}`

Errors are JSON: `{"error": "message"}`.
