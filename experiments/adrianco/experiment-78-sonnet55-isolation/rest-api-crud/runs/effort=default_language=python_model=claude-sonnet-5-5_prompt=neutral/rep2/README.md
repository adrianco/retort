# Book Collection API

Python 3 standard library only (WSGI + `sqlite3`); no dependencies to run.

## Run
    python app.py            # http://127.0.0.1:8000  (env: PORT, BOOKS_DB)

## Test
    pip install pytest && python -m pytest

## Endpoints
- `POST /books` `{title, author, year?, isbn?}` → 201 (title, author required → 400 otherwise)
- `GET /books[?author=Name]` → 200 list
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` → 200 / 400 / 404
- `DELETE /books/{id}` → 200 / 404
- `GET /health` → `{"status": "ok"}`
