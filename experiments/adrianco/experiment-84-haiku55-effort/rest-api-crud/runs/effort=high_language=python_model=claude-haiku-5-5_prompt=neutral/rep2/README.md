# Book Collection API

A small JSON REST API for managing a book collection, written in Python with
SQLite storage. It uses only the standard library at runtime; `pytest` is needed
only to run the tests.

## Requirements

- Python 3.10 or newer

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # pytest, for running the tests
```

No packages are needed to run the service itself.

## Run

```bash
python -m bookapi                          # http://127.0.0.1:8000, data in ./books.db
python -m bookapi --port 9000 --db /tmp/books.db
python -m bookapi --help
```

| Option   | Default       | Meaning                              |
|----------|---------------|--------------------------------------|
| `--host` | `127.0.0.1`   | Interface to bind                    |
| `--port` | `8000`        | Port to listen on                    |
| `--db`   | `books.db`    | SQLite database file (created if missing) |

Stop the server with `Ctrl+C`.

## Test

```bash
python -m pytest
```

The suite contains 57 tests in three files:

- `tests/test_validation.py` — payload validation and normalisation
- `tests/test_store.py` — SQLite storage, including persistence across reconnects
- `tests/test_api.py` — end-to-end HTTP tests against a live server on a free port,
  including a concurrent-write test

## API

All requests and responses use JSON. Errors share one shape:

```json
{"error": "Validation failed", "details": {"title": "is required"}}
```

### Book resource

| Field    | Type            | Required | Notes                                              |
|----------|-----------------|----------|----------------------------------------------------|
| `id`     | integer         | server   | Assigned on create; read-only                      |
| `title`  | string          | yes      | 1–500 characters after trimming whitespace         |
| `author` | string          | yes      | 1–500 characters after trimming whitespace         |
| `year`   | integer or null | no       | Between 1000 and next calendar year                |
| `isbn`   | string or null  | no       | ISBN-10 or ISBN-13; hyphens and spaces are stripped and the value is stored uppercase |

### Endpoints

| Method   | Path           | Success                               | Errors                    |
|----------|----------------|---------------------------------------|---------------------------|
| `POST`   | `/books`       | `201` + book, `Location` header       | `400` validation          |
| `GET`    | `/books`       | `200` + array of books                | `400` blank `author` filter |
| `GET`    | `/books/{id}`  | `200` + book                          | `404`                     |
| `PUT`    | `/books/{id}`  | `200` + updated book                  | `400` validation, `404`   |
| `DELETE` | `/books/{id}`  | `204` (no body)                       | `404`                     |
| `GET`    | `/health`      | `200` `{"status": "ok"}`              | `503` if the database is unreachable |

Other errors: `404` for unknown paths, `405` for an unsupported method on a known
path (with an `Allow` header), `413` for bodies over 1 MB, `400` for malformed
JSON or a non-object body, and `500` for unexpected failures.

`GET /books` returns books in insertion order. The optional `author` query
parameter is an exact match that ignores case, so `?author=jane%20austen` matches
`Jane Austen`. Partial matches are not supported.

`PUT` replaces the whole book. Send `title` and `author`; any omitted `year` or
`isbn` is cleared to `null`.

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'

# List, or filter by author
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=frank%20herbert'

# Get one
curl http://127.0.0.1:8000/books/1

# Replace
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Project layout

```
bookapi/
  __main__.py    command-line entry point (python -m bookapi)
  server.py      routing, JSON encoding and HTTP handler
  store.py       SQLite persistence
  validation.py  payload validation and normalisation
tests/           pytest suite
pyproject.toml   pytest configuration
requirements-dev.txt
```

## Design notes

- **Standard library only.** The service uses `http.server` and `sqlite3`, so
  there is nothing to install beyond Python. `server.py` keeps routing in
  `handle_request`, a plain function that takes values and returns a response, so
  routing logic can be tested without a socket.
- **Concurrency.** The HTTP server is threaded. A single SQLite connection is
  shared and guarded by a lock, which keeps writes serialised.
- **Validation runs before any database access.** Every problem with a payload is
  reported in one response, not just the first.
- **ISBN check digits are not verified.** Only the format (length and character
  set) is checked. Add a checksum test to `validation.py` if you need that.
- **Duplicate ISBNs are allowed.** A collection can hold more than one copy of an
  edition.
