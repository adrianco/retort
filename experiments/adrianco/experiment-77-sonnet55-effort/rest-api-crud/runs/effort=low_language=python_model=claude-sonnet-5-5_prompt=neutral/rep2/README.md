# Book Collection API

Python standard-library REST service (`http.server` + `sqlite3`); no third-party runtime dependencies.

## Run
    python app.py            # env: HOST (127.0.0.1), PORT (8000), DB_PATH (books.db)

## Endpoints
- `POST /books` — body `{title, author, year?, isbn?}` (title/author required) → 201
- `GET /books[?author=Name]` → 200
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` — full update, same validation → 200 / 400 / 404
- `DELETE /books/{id}` → 204 / 404
- `GET /health` → `{"status": "ok"}`

## Test
    pip install pytest
    python -m pytest
