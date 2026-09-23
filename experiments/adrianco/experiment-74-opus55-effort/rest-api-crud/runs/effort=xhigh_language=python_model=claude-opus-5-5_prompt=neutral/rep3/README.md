# Book Collection API

A small REST API for managing a book collection, backed by SQLite.

It is written against the Python standard library only (`wsgiref`, `sqlite3`,
`json`), so there is nothing to install to run it. `pytest` is the only
development dependency.

## Requirements

- Python 3.10 or newer

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Running the server

```bash
python -m books_api
# Serving on http://127.0.0.1:8000 (database: books.db)
```

Options (each can also be set with an environment variable):

| Flag     | Environment variable | Default     | Meaning                     |
|----------|----------------------|-------------|-----------------------------|
| `--host` | `BOOKS_API_HOST`     | `127.0.0.1` | Interface to bind           |
| `--port` | `BOOKS_API_PORT`     | `8000`      | Port to listen on           |
| `--db`   | `BOOKS_API_DB`       | `books.db`  | SQLite database file path   |

The database file and its parent directory are created on first start. Stop
the server with Ctrl+C or `SIGTERM`.

The bundled server is the standard library's threaded WSGI server, which is
fine for local and small-scale use. The app is a standard WSGI application,
so for production you can run it under any WSGI server instead, e.g.
`gunicorn 'books_api:create_app()'`. `create_app()` reads `BOOKS_API_DB`.

## API

All request and response bodies are JSON. Requests with a body must send
`Content-Type: application/json`.

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
```

| Method   | Path          | Description                        | Success                        |
|----------|---------------|------------------------------------|--------------------------------|
| `GET`    | `/health`     | Health check (also checks the DB)  | `200` (`503` if DB unreachable) |
| `POST`   | `/books`      | Create a book                      | `201` + `Location` header      |
| `GET`    | `/books`      | List books; optional `?author=`    | `200`                          |
| `GET`    | `/books/{id}` | Get one book                       | `200`                          |
| `PUT`    | `/books/{id}` | Replace a book                     | `200`                          |
| `DELETE` | `/books/{id}` | Delete a book                      | `204` (empty body)             |

### Fields and validation

| Field    | Required | Rules                                                                 |
|----------|----------|-----------------------------------------------------------------------|
| `title`  | yes      | Non-blank string, at most 500 characters; surrounding whitespace is trimmed |
| `author` | yes      | Non-blank string, at most 500 characters; surrounding whitespace is trimmed |
| `year`   | no       | Integer from 1 to the current year                                    |
| `isbn`   | no       | ISBN-10 or ISBN-13: 10 or 13 digits (an ISBN-10 may end in `X`), optionally separated by hyphens or spaces. Stored as sent |

- Optional fields that are omitted, `null` or (for `isbn`) blank are stored as `null`.
- `id` is assigned by the server and is read-only. An `id` in a request body is
  ignored, so a book fetched with `GET` can be edited and sent straight back with `PUT`.
- Any other field is rejected, so a typo such as `"autor"` is reported instead
  of being silently dropped.
- `PUT` replaces the whole book: `title` and `author` are required, and
  omitted optional fields are reset to `null`.
- `?author=` is a case-insensitive substring match: `?author=austen` finds
  books by "Jane Austen". A blank value returns all books.
- IDs are never reused: once a book is deleted, its ID keeps returning `404`.

### Errors

Errors return an appropriate status code and a JSON body with an `error`
message. Validation errors also include per-field `details`:

```json
{"error": "Validation failed", "details": {"title": "title is required", "year": "year must be an integer"}}
```

| Status | When                                                             |
|--------|------------------------------------------------------------------|
| `400`  | Invalid JSON, body is not a JSON object, or validation failed    |
| `404`  | No such book, or unknown path                                    |
| `405`  | Method not supported on that path (see the `Allow` header)       |
| `413`  | Request body larger than 1 MiB                                   |
| `415`  | `Content-Type` is not `application/json`                         |
| `500`  | Unexpected server error (details are logged, not returned)       |

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'

# List all, or filter by author
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=herbert'

# Get, replace, delete
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Running the tests

```bash
python -m pytest
```

| File                      | What it covers                                                          |
|---------------------------|-------------------------------------------------------------------------|
| `tests/test_validation.py` | Unit tests for payload validation rules                                |
| `tests/test_storage.py`    | Unit tests for the SQLite repository (CRUD, filtering, persistence)    |
| `tests/test_api.py`        | Every endpoint, status code and error case, run in-process through `wsgiref`'s WSGI validator |
| `tests/test_server.py`     | End-to-end over real HTTP: CRUD round trip, data on disk, 50 concurrent creates |
| `tests/test_cli.py`        | `python -m books_api` as a child process: startup, `SIGTERM` shutdown, startup errors |

## Project layout

```
books_api/
  __init__.py     create_app() factory for WSGI servers
  __main__.py     `python -m books_api` entry point
  app.py          WSGI app: routing, JSON handling, HTTP errors
  storage.py      BookRepository: SQLite persistence
  validation.py   Request payload validation
  server.py       Command-line server (threaded wsgiref)
tests/            pytest suite
```
