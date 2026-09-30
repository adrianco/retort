# Book Collection API

REST API for managing books, built with the Python standard library
(`http.server` + `sqlite3`) — no third-party runtime dependencies.

## Run

    python app.py            # PORT (default 8000), DB_PATH (default books.db)

## Endpoints

| Method | Path          | Description                          |
|--------|---------------|--------------------------------------|
| POST   | /books        | Create (title, author required; year, isbn optional) → 201 |
| GET    | /books        | List; optional `?author=` filter     |
| GET    | /books/{id}   | Get one (404 if missing)             |
| PUT    | /books/{id}   | Update (same validation as create)   |
| DELETE | /books/{id}   | Delete → 204                         |
| GET    | /health       | `{"status": "ok"}`                   |

Invalid input returns 400 with `{"error": ...}`.

## Test

    pip install pytest
    pytest
