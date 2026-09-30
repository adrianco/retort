# Book Collection API

Python standard library only (`http.server` + `sqlite3`); no dependencies to run.

## Run
    python app.py            # http://127.0.0.1:8000, PORT env to change
    BOOKS_DB=/path/to.db python app.py

## Endpoints
- `GET /health`
- `POST /books` — JSON `{title, author, year, isbn}` (title and author required) → 201
- `GET /books[?author=NAME]`
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` — full update → 200 / 400 / 404
- `DELETE /books/{id}` → 204 / 404

## Test
    pip install pytest
    pytest
