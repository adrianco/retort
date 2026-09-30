# Book Collection API

A small REST API for managing a collection of books, written in Python with **no
third-party runtime dependencies**: a standard-library WSGI application
(`wsgiref` server) storing data in **SQLite** (`sqlite3`). Only the tests need
`pytest`.

## Requirements

- Python 3.9 or newer (developed and tested on 3.14)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest pytest-cov     # only needed to run the tests
```

The service itself needs nothing beyond the standard library.

## Run

```bash
PYTHONPATH=src python -m bookapi                      # http://127.0.0.1:8000, db: books.db
PYTHONPATH=src python -m bookapi --port 9000 --db /tmp/library.db
```

Options can also be set via environment variables: `HOST`, `PORT`, `BOOKS_DB`.
The database file and table are created on first start. Optionally,
`pip install -e .` installs the package and a `bookapi` command, after which
`PYTHONPATH=src` is no longer needed.

## Test

```bash
python -m pytest                       # run all tests
python -m pytest --cov=bookapi         # with coverage
```

The suite covers the endpoints in-process through the WSGI interface, the
storage and validation layers, and one end-to-end lifecycle over real HTTP.

## API

All request and response bodies are JSON (`Content-Type: application/json; charset=utf-8`).

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Field    | Rules                                                     |
|----------|-----------------------------------------------------------|
| `title`  | **required**, non-empty string, at most 255 characters    |
| `author` | **required**, non-empty string, at most 255 characters    |
| `year`   | optional integer from 1 to 9999                           |
| `isbn`   | optional string, at most 32 characters                    |

Strings are trimmed of surrounding whitespace; unknown fields are ignored.

| Method   | Path           | Description                                   | Success                          |
|----------|----------------|-----------------------------------------------|----------------------------------|
| `POST`   | `/books`       | Create a book                                 | `201` + book, `Location` header  |
| `GET`    | `/books`       | List books, optional `?author=` filter        | `200` + array of books           |
| `GET`    | `/books/{id}`  | Get one book                                  | `200` + book                     |
| `PUT`    | `/books/{id}`  | Replace a book (same rules as create)         | `200` + updated book             |
| `DELETE` | `/books/{id}`  | Delete a book                                 | `204`, no body                   |
| `GET`    | `/health`      | Health check (verifies the database responds) | `200` `{"status": "ok"}`         |

Notes:

- `?author=` matches the full author name, ignoring case (`?author=george orwell`
  finds "George Orwell"; `?author=Orwell` does not). A blank value is ignored.
  Results are ordered by id.
- `PUT` is a full replacement: optional fields omitted from the body are reset to `null`.
- `/health` returns `503` `{"status": "unavailable"}` if the database cannot be queried.

### Errors

Errors are JSON objects with an `error` message:

| Status | When                                                                  |
|--------|-----------------------------------------------------------------------|
| `400`  | Invalid JSON, body is not an object, or a field fails validation      |
| `404`  | Unknown route, or no book with that id (including non-numeric ids)    |
| `405`  | Method not supported on that path (an `Allow` header lists the valid ones) |
| `413`  | Request body larger than 1 MiB                                        |
| `500`  | Unexpected server error (details are logged, not returned)            |

Validation failures list every offending field:

```json
{"error": "Validation failed", "details": {"title": "is required", "year": "must be an integer"}}
```

### Example

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Project layout

```
src/bookapi/
  app.py          WSGI app: routing, JSON handling, error mapping
  store.py        SQLite repository (thread-safe, parameterised queries)
  validation.py   Input validation
  __main__.py     Command-line entry point (threaded wsgiref server)
tests/            pytest suite
```

`wsgiref` is intended for development and light use. `bookapi.create_app("books.db")`
returns a standard WSGI callable, so it can be hosted by any WSGI server instead.
