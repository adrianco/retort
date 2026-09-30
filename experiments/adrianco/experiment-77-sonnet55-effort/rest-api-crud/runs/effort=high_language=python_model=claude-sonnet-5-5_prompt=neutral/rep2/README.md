# Book Collection API

A REST API for managing a book collection, backed by SQLite.

No web framework was specified for this task, so the service uses only the Python
standard library (`http.server` + `sqlite3`). There are no runtime dependencies;
`pytest` is needed only to run the tests.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate   # optional
pip install pytest                                 # tests only
```

## Run

```bash
python bookapi.py
```

The server listens on `http://127.0.0.1:8000`. Configure with environment variables:
`HOST`, `PORT`, and `BOOKS_DB` (SQLite file path, default `books.db`).

## Endpoints

| Method | Path            | Description                                   | Success |
|--------|-----------------|-----------------------------------------------|---------|
| GET    | `/health`       | Health check → `{"status": "ok"}`             | 200     |
| POST   | `/books`        | Create a book                                 | 201     |
| GET    | `/books`        | List books; optional `?author=` filter        | 200     |
| GET    | `/books/{id}`   | Get one book                                  | 200     |
| PUT    | `/books/{id}`   | Replace a book                                | 200     |
| DELETE | `/books/{id}`   | Delete a book                                 | 204     |

Book fields: `title` (required string), `author` (required string), `year`
(optional integer), `isbn` (optional string). `id` is assigned by the server.
`PUT` replaces the whole record, so `title` and `author` are required and omitted
optional fields are reset to `null`. The `?author=` filter is an exact,
case-insensitive match.

Errors are JSON: `{"error": "..."}`. Validation failures return `400` with a
`details` object per field; unknown books/routes return `404`; unsupported methods
return `405`.

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
```

## Tests

```bash
python -m pytest -v
```
