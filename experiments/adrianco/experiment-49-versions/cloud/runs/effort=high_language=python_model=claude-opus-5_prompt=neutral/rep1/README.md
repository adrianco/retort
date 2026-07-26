# Book Collection API

A small REST API for managing a book collection, written in Python with **no third-party
dependencies** — just the standard library (`wsgiref` for HTTP, `sqlite3` for storage).
That means there is nothing to install: clone it and run it.

## Requirements

- Python 3.9+
- `pytest` (only to run the test suite)

## Run

```bash
python3 -m bookapi                      # http://127.0.0.1:8000, data in ./books.db
python3 -m bookapi --port 9000          # different port
python3 -m bookapi --db /tmp/books.db   # different database file
python3 -m bookapi --host 0.0.0.0       # listen on all interfaces
```

The SQLite file and its schema are created automatically on first start.

## Test

```bash
python3 -m pytest          # or: pytest
```

81 tests covering validation rules, the storage layer, and the HTTP API end to end.
The API tests start the real server on an ephemeral port and talk to it over a real
socket, so nothing about the request path is mocked.

## API

All request and response bodies are JSON. `POST`/`PUT` require
`Content-Type: application/json`.

| Method   | Path          | Description                          | Success |
| -------- | ------------- | ------------------------------------ | ------- |
| `GET`    | `/health`     | Service and database health          | `200`   |
| `POST`   | `/books`      | Create a book                        | `201`   |
| `GET`    | `/books`      | List books, optional `?author=`      | `200`   |
| `GET`    | `/books/{id}` | Fetch one book                       | `200`   |
| `PUT`    | `/books/{id}` | Replace a book                       | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                        | `204`   |

### Book object

```json
{
  "id": 1,
  "title": "Nineteen Eighty-Four",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0-452-28423-4",
  "created_at": "2024-05-01T10:15:30.123Z",
  "updated_at": "2024-05-01T10:15:30.123Z"
}
```

### Examples

```bash
# Health check
curl localhost:8000/health
# {"status": "ok", "database": "ok"}

# Create — responds 201 with a Location header
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0-452-28423-4"}'

# List everything (newest first)
curl localhost:8000/books

# Filter by author — case-insensitive substring match
curl 'localhost:8000/books?author=orwell'

# Fetch one
curl localhost:8000/books/1

# Replace — PUT is a full replacement, so omitted optional fields are cleared
curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949}'

# Delete — 204 with an empty body
curl -i -X DELETE localhost:8000/books/1
```

## Validation

| Field    | Rules                                                                        |
| -------- | ---------------------------------------------------------------------------- |
| `title`  | **Required.** String, trimmed, non-empty, ≤ 500 characters.                  |
| `author` | **Required.** String, trimmed, non-empty, ≤ 255 characters.                  |
| `year`   | Optional. Integer (or a numeric string) between 1 and 9999. `null` allowed.  |
| `isbn`   | Optional. ISBN-10 or ISBN-13; hyphens and spaces allowed. `null` allowed.    |

Unknown fields in the payload are ignored, so a response body can be sent straight
back as a `PUT` without stripping `id` or the timestamps first. A client-supplied
`id` is never honoured.

Every invalid field is reported in one response rather than one at a time:

```json
{
  "error": "Validation failed",
  "details": {
    "title": "title is required.",
    "year": "year must be an integer."
  }
}
```

## Status codes

| Code  | When                                                                     |
| ----- | ------------------------------------------------------------------------ |
| `200` | Successful `GET` or `PUT`                                                |
| `201` | Book created (includes a `Location` header)                              |
| `204` | Book deleted (empty body)                                                |
| `400` | Validation failure, malformed/empty JSON, or a non-object body           |
| `404` | Unknown route, or a book id that does not exist                          |
| `405` | Wrong method for a known path (includes an `Allow` header)               |
| `413` | Request body larger than 1 MiB                                           |
| `415` | `Content-Type` is not `application/json`                                 |
| `503` | `/health` only — the database is not reachable                           |

Errors always return `{"error": "<message>"}`, plus a `"details"` object where
there is more to say.

## Design notes

- **Layering.** `validation.py` (rules), `db.py` (SQL), `app.py` (HTTP routing) and
  `server.py` (process entry point) are independent, so the rules and the storage
  layer are unit-testable without an HTTP server.
- **Concurrency.** Requests are served on threads. A single SQLite connection is
  shared behind a lock, which serialises writes and keeps behaviour identical for
  file-backed and `:memory:` databases.
- **SQL safety.** Every query is parameterised. The `?author=` filter escapes `%`
  and `_` so user input cannot act as a `LIKE` wildcard.
- **`PUT` is a replacement**, not a merge: `title` and `author` are required, and
  omitting `year` or `isbn` clears them. `created_at` is preserved; `updated_at`
  is refreshed.
- **List ordering** is newest first (`id DESC`).

## Layout

```
bookapi/
  __init__.py      public exports
  validation.py    payload rules, framework-agnostic
  db.py            SQLite schema and CRUD
  app.py           WSGI app: routing, JSON encoding, error mapping
  server.py        threaded HTTP server + CLI
  __main__.py      python -m bookapi
tests/
  test_validation.py   validation rules
  test_db.py           storage layer, persistence, concurrent writes
  test_api.py          end-to-end HTTP over a real socket
conftest.py        server + client fixtures
```
