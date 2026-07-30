# Book Collection API

A small REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/uvicorn main:app --reload
```

The service listens on http://127.0.0.1:8000. Interactive docs at `/docs`.
Data is stored in `books.db` (override with the `BOOKS_DB` environment variable).

## Tests

```bash
.venv/bin/python -m pytest
```

## Endpoints

| Method | Path | Description | Success |
|---|---|---|---|
| GET | `/health` | Health check | 200 |
| POST | `/books` | Create a book | 201 |
| GET | `/books` | List books, optional `?author=` exact-match filter | 200 |
| GET | `/books/{id}` | Fetch one book | 200 |
| PUT | `/books/{id}` | Replace a book | 200 |
| DELETE | `/books/{id}` | Delete a book | 204 |

Book fields: `title` (required, non-blank), `author` (required, non-blank),
`year` (optional integer), `isbn` (optional string).

Errors: `404` with `{"detail": "Book not found"}` for unknown IDs, `422` with
FastAPI's validation detail for invalid request bodies.

## Examples

```bash
curl -X POST localhost:8000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8000/books/1
```

## Files

- `main.py` — FastAPI app, routes, request/response models
- `db.py` — SQLite storage layer
- `test_api.py` — integration tests (each runs against a temporary database)
