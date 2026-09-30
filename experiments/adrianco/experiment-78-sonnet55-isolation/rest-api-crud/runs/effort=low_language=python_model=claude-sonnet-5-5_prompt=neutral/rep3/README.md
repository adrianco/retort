# Book Collection API

Pure standard-library Python (3.8+) REST API backed by SQLite. No dependencies.

## Run
    python app.py [port]      # default 8000, creates books.db

## Endpoints
- `POST /books` — body `{title, author, year, isbn}` (title, author required) → 201
- `GET /books[?author=NAME]` — list
- `GET /books/{id}` — fetch (404 if missing)
- `PUT /books/{id}` — replace/update (400 invalid, 404 missing)
- `DELETE /books/{id}` — delete → 200 `{"deleted": id}`
- `GET /health` → `{"status": "ok"}`

## Test
    pip install pytest
    pytest
