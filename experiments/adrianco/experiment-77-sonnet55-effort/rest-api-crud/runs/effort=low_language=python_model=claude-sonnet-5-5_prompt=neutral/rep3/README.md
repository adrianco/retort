# Book Collection API

REST API for managing books. Pure Python standard library (`http.server`, `sqlite3`); no dependencies to run.

## Setup & run
```
python app.py            # serves on :8000; PORT and DB_PATH env vars override (default DB: books.db)
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| POST | /books | body: `title`, `author` (required), `year` (int), `isbn` -> 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full update, same validation as POST |
| DELETE | /books/{id} | 204, or 404 |
| GET | /health | `{"status": "ok"}` |

Errors are JSON: `{"error": "..."}` with 400 (validation) or 404.

## Tests
```
pip install pytest
pytest
```
