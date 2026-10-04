# Books API

A small REST service for managing a book collection. It is written in Python
using only the standard library (`wsgiref` for HTTP, `sqlite3` for storage), so
there is nothing to install to run it.

## Requirements

- Python 3.9 or newer
- `pytest` to run the tests (the only third-party dependency, test-only)

## Run

```bash
python3 -m books_api
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db` in
the current directory (created on first start).

| Option   | Environment variable | Default     | Meaning                                   |
|----------|----------------------|-------------|-------------------------------------------|
| `--host` | `BOOKS_HOST`         | `127.0.0.1` | Interface to bind (`0.0.0.0` for all)     |
| `--port` | `BOOKS_PORT`         | `8000`      | Port to listen on                         |
| `--db`   | `BOOKS_DB`           | `books.db`  | SQLite file, or `:memory:` for throwaway  |

```bash
python3 -m books_api --port 9000 --db /tmp/books.db
```

The server is `wsgiref`'s, which is fine for local use and light traffic. For
anything more, serve the same WSGI app with a production server, e.g.
`gunicorn 'books_api:create_app("books.db")'`.

## Test

```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest
```

Add `--cov=books_api` for a coverage report. Most tests call the WSGI app
in-process against an in-memory database; `tests/test_server.py` also starts a
real HTTP server on a free port with an on-disk database.

## API

All request and response bodies are JSON. A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
```

| Method   | Path          | Success          | Description                          |
|----------|---------------|------------------|--------------------------------------|
| `GET`    | `/health`     | `200`            | Health check: `{"status": "ok"}`     |
| `POST`   | `/books`      | `201` + book     | Create a book                        |
| `GET`    | `/books`      | `200` + array    | List books, optional `?author=`      |
| `GET`    | `/books/{id}` | `200` + book     | Get one book                         |
| `PUT`    | `/books/{id}` | `200` + book     | Replace a book                       |
| `DELETE` | `/books/{id}` | `204`, no body   | Delete a book                        |

### Fields

| Field    | Type    | Rules                                                        |
|----------|---------|--------------------------------------------------------------|
| `title`  | string  | **Required**, not blank, at most 500 characters              |
| `author` | string  | **Required**, not blank, at most 500 characters              |
| `year`   | integer | Optional, 1–9999                                             |
| `isbn`   | string  | Optional, at most 32 characters                              |

Behaviour worth knowing:

- Strings are trimmed of surrounding whitespace. Omitted optional fields are
  stored and returned as `null`.
- `id` is assigned by the server and never reused; an `id` in a request body,
  like any other unknown key, is ignored.
- `PUT` replaces the whole book: `title` and `author` are required again, and an
  omitted `year` or `isbn` is reset to `null`.
- `?author=` is an exact, case-insensitive match on the full author name (case
  folding covers ASCII letters only, as that is what SQLite's `NOCASE` does).
- The ISBN format and checksum are not verified, and duplicates are allowed.
- `POST /books` responds with a `Location` header pointing at the new book.

### Errors

Errors are JSON too. Validation failures list every offending field:

```json
{"error": "Validation failed", "details": {"title": "is required", "year": "must be an integer"}}
```

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Body is missing, not valid JSON, not an object, or fails validation  |
| `404`  | Unknown path, or no book with that id                                |
| `405`  | Method not supported on the path (see the `Allow` header)            |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected server error                                              |
| `503`  | `/health` only: the database is not usable                           |

### Examples

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Layout

```
books_api/
  app.py          WSGI application: routing, handlers, JSON responses
  db.py           BookRepository: SQLite schema and queries
  validation.py   Payload validation
  __main__.py     Command-line entry point and HTTP server
tests/
  conftest.py     In-process WSGI test client and fixtures
  test_api.py     Endpoint behaviour, validation and error handling
  test_server.py  Real HTTP server, concurrency, persistence, CLI options
```
