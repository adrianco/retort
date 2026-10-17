# Book Collection API

A REST API for managing a book collection, built with Python's standard library
(`http.server` and `sqlite3`). It has no third-party runtime dependencies.

## Requirements

- Python 3.10 or newer (uses `X | None` type syntax)
- pytest, only if you want to run the test suite

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest        # only needed for running tests
```

## Run

```bash
python -m bookapi                          # http://127.0.0.1:8000, data in ./books.db
python -m bookapi --port 9000 --db my.db   # custom port and database file
```

Options can also be set with environment variables: `BOOKAPI_HOST`, `BOOKAPI_PORT`,
`BOOKAPI_DB`. Command-line flags take precedence over the environment.

The database file and its table are created on first start.

## Test

```bash
python -m pytest
```

The suite has 48 tests in three files:

- `tests/test_validation.py`: input rules (required fields, types, year range, ISBN checksums)
- `tests/test_store.py`: SQLite persistence, id allocation, author filtering
- `tests/test_api.py`: end-to-end HTTP tests against a real server on an ephemeral port

## Endpoints

| Method   | Path          | Success                     | Notes                              |
|----------|---------------|-----------------------------|------------------------------------|
| `POST`   | `/books`      | `201 Created` + `Location`  | Create a book                      |
| `GET`    | `/books`      | `200 OK`                    | List books; `?author=` filters     |
| `GET`    | `/books/{id}` | `200 OK`                    | Fetch one book                     |
| `PUT`    | `/books/{id}` | `200 OK`                    | Replace a book (full update)       |
| `DELETE` | `/books/{id}` | `204 No Content`            | Delete a book                      |
| `GET`    | `/health`     | `200 OK`                    | Liveness and database check        |

### Book fields

| Field    | Type    | Required | Rules                                                        |
|----------|---------|----------|--------------------------------------------------------------|
| `id`     | integer | —        | Assigned by the server; never reused after delete            |
| `title`  | string  | yes      | Non-blank after trimming; max 500 characters                 |
| `author` | string  | yes      | Non-blank after trimming; max 500 characters                 |
| `year`   | integer | no       | 1 to next calendar year                                      |
| `isbn`   | string  | no       | Valid ISBN-10 or ISBN-13 (checksum checked); hyphens and spaces are stripped and the result is stored |

Omitted optional fields are returned as `null`.

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'

# List, filtered by author (exact match, case-insensitive)
curl "http://127.0.0.1:8000/books?author=frank%20herbert"

# Update (all of title and author are required, as with any PUT)
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# Delete
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

### Errors

All error responses are JSON of the form `{"error": "<code>", "message": "..."}`.

| Status | `error`              | When                                                               |
|--------|----------------------|--------------------------------------------------------------------|
| 400    | `validation_failed`  | Field rules violated; `details` maps each field to a message       |
| 400    | `invalid_json`       | Body missing or not valid JSON                                     |
| 404    | `not_found`         | Unknown path, or no book with that id (non-numeric ids also 404)   |
| 405    | `method_not_allowed` | Known path, unsupported verb; `Allow` header lists valid verbs     |
| 413    | `payload_too_large`  | Body larger than 1 MiB                                             |
| 500    | `internal_error`     | Unexpected failure (logged server-side)                            |
| 503    | `unavailable`        | `/health` only, when the database cannot be reached                |

Example validation failure:

```json
{
  "error": "validation_failed",
  "message": "request validation failed",
  "details": {"title": "must not be blank", "author": "is required"}
}
```

## Layout

```
bookapi/
  __main__.py     CLI entry point (python -m bookapi)
  http_app.py     routing, JSON handling, request/response mapping
  store.py        SQLite repository
  validation.py   payload validation and ISBN checksums
tests/
  test_api.py
  test_store.py
  test_validation.py
pytest.ini
```

## Notes

- The server uses one shared SQLite connection guarded by a lock. This is simple and
  correct for a single process. It is not a horizontally scalable design. Move to a
  connection pool or a client/server database if you need multiple instances.
- The server is intended for local use and does not implement authentication or TLS.
  Put it behind a reverse proxy if you expose it.
