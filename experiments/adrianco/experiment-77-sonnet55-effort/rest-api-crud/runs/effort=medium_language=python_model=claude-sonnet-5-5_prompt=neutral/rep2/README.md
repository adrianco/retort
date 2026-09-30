# Book Collection API

REST API for managing books. Python standard library only (WSGI + `sqlite3`); no dependencies to install.

## Run

```bash
python app.py            # http://127.0.0.1:8000
PORT=9000 DB_PATH=/tmp/books.db python app.py
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/books` | Create (`title`, `author` required; `year` int, `isbn` string optional) → 201 |
| GET | `/books` | List; optional `?author=` exact-match filter |
| GET | `/books/{id}` | Fetch one (404 if missing) |
| PUT | `/books/{id}` | Replace/update (same validation as POST) |
| DELETE | `/books/{id}` | Delete → 204 |

Errors are JSON: `{"error": "..."}` with 400 (validation), 404, or 405.

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Tests

```bash
pip install pytest
python -m pytest -v
```
