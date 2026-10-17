# Book Collection API

A small REST API for managing a book collection. It is built on the Python standard library
(`http.server` and `sqlite3`), so it has no runtime dependencies. Data is stored in a single SQLite file.

## Requirements

- Python 3.10 or newer (developed and tested with Python 3.13)
- `pytest` for running the tests (listed in `requirements-dev.txt`)

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
```

The runtime itself needs nothing beyond the standard library, so `pip install` is only needed for the tests.

## Run

```bash
venv/bin/python -m book_api                   # http://127.0.0.1:8000, database ./books.db
venv/bin/python -m book_api --port 9000 --db /tmp/books.db
```

| Option        | Default       | Meaning                              |
|---------------|---------------|--------------------------------------|
| `--host`      | `127.0.0.1`   | Interface to bind                    |
| `--port`      | `8000`        | Port to listen on                    |
| `--db`        | `books.db`    | Path to the SQLite database file     |
| `--log-level` | `INFO`        | Logging level (request log lines)    |

Stop the server with Ctrl+C. The database file is created on first start and its contents persist across restarts.

## Endpoints

| Method   | Path          | Success                | Other responses                              |
|----------|---------------|------------------------|----------------------------------------------|
| `POST`   | `/books`      | `201` book + `Location`| `400` validation error                       |
| `GET`    | `/books`      | `200` array of books   | Optional `?author=` filter                   |
| `GET`    | `/books/{id}` | `200` book             | `404` not found                              |
| `PUT`    | `/books/{id}` | `200` updated book     | `400` validation error, `404` not found      |
| `DELETE` | `/books/{id}` | `204` no content       | `404` not found                              |
| `GET`    | `/health`     | `200` `{"status":"ok"}`| `503` if the database cannot be queried      |

A book has the shape `{"id", "title", "author", "year", "isbn"}`. `year` and `isbn` may be `null`.

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'
# -> 201 Created, Location: /books/1
# -> {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}

# List, optionally filtered by author (exact match, ignoring case)
curl http://127.0.0.1:8000/books
curl "http://127.0.0.1:8000/books?author=frank%20herbert"

# Get one
curl http://127.0.0.1:8000/books/1

# Replace (title and author are required, as on create)
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

# Delete
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

### Validation rules

- `title` and `author`: required. They must be non-blank strings of at most 500 characters. Surrounding whitespace is stripped.
- `year`: optional integer from 1450 to 2100 inclusive. Strings and booleans are rejected.
- `isbn`: optional. Hyphens and spaces are removed and the result is stored in digits-only form (`X` is kept for ISBN-10). It must then be 10 or 13 characters long. The checksum is not verified. An empty value is stored as `null`.
- Unknown fields are ignored. A `null` value for `year` or `isbn`, or a blank `isbn`, is stored as `null`.
- The request body must be a JSON object and must not exceed 1 MiB.

Validation failures return `400` with every failing field reported at once:

```json
{"error": "Validation failed", "details": {"title": "is required", "author": "is required"}}
```

### Error format

Every error response is JSON of the form `{"error": "<message>"}`. Requests to a known path with an unsupported method return `405` with an `Allow` header. Unexpected failures return `500` with a generic message, and the traceback is written to the server log.

## Tests

```bash
venv/bin/python -m pytest
```

The suite has 51 tests in three groups:

- `tests/test_validation.py`: unit tests for payload validation and normalisation.
- `tests/test_repository.py`: SQLite storage behaviour, including persistence across reopening the database file.
- `tests/test_api.py`: integration tests. Each test sends real HTTP requests to a server bound to an ephemeral port.

## Project layout

```
book_api/
  __main__.py     command-line entry point (python -m book_api)
  server.py       HTTP routing, JSON responses and error mapping
  validation.py   input validation and normalisation
  repository.py   SQLite storage
  models.py       Book and BookFields dataclasses
tests/            pytest suite
pytest.ini
requirements-dev.txt
```

## Design notes

- **Standard library only.** `ThreadingHTTPServer` serves requests and a single SQLite connection is shared behind a lock. This suits development, demos and small collections. It is not intended as a production deployment: there is no authentication, no TLS and no pagination.
- **`PUT` replaces the whole book.** Fields omitted from a `PUT` body are cleared, and `title` and `author` are required again. Use `PUT` with the full representation. `PUT` to a missing id returns `404` and does not create the book.
- **Author filter.** `?author=` matches the stored author exactly, ignoring case for ASCII letters (SQLite's `NOCASE`). It is not a substring search. A blank `?author=` returns every book.
- **Ordering.** `GET /books` returns books in ascending id order (creation order).
