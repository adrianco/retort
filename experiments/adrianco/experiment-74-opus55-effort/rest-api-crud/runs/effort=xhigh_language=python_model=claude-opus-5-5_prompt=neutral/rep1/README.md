# Books API

A REST API for managing a book collection. It is written in Python using only
the standard library: a WSGI application served by `wsgiref`, with data stored
in SQLite through `sqlite3`. Running the service needs no third-party packages.
Only the test suite needs `pytest`.

## Requirements

- Python 3.10 or newer (tested on 3.10 and 3.14)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt     # only pytest, needed to run the tests
```

## Running the server

```bash
python -m books_api                 # http://127.0.0.1:8000, data in ./books.db
python -m books_api --host 0.0.0.0 --port 8080 --db /var/lib/books/books.db
python -m books_api --db :memory:   # throwaway in-memory database
```

| Option   | Environment variable | Default     | Meaning                                  |
|----------|----------------------|-------------|------------------------------------------|
| `--host` | `BOOKS_API_HOST`     | `127.0.0.1` | Interface to bind                        |
| `--port` | `BOOKS_API_PORT`     | `8000`      | Port to listen on (`0` = any free port)  |
| `--db`   | `BOOKS_API_DB`       | `books.db`  | SQLite database file, or `:memory:`      |

The database file and table are created on first start. Stop the server with
Ctrl+C or SIGTERM; both shut it down cleanly.

`books_api.create_app()` returns a standard WSGI application, reading
`BOOKS_API_DB` for its database. You can host it with any WSGI server instead
of the built-in one.

## API

| Method   | Path          | Success                | Errors          |
|----------|---------------|------------------------|-----------------|
| `GET`    | `/health`     | `200`                  | `503`           |
| `POST`   | `/books`      | `201` + `Location`     | `400`, `413`    |
| `GET`    | `/books`      | `200` (JSON array)     |                 |
| `GET`    | `/books/{id}` | `200`                  | `404`           |
| `PUT`    | `/books/{id}` | `200`                  | `400`, `404`    |
| `DELETE` | `/books/{id}` | `204` (empty body)     | `404`           |

Other methods on these paths return `405` with an `Allow` header. Unknown paths
return `404`. `HEAD` works wherever `GET` does.

### Book fields

| Field    | Type    | Rules                                                                          |
|----------|---------|--------------------------------------------------------------------------------|
| `id`     | integer | Assigned by the server. Ignored if sent. Never reused after a delete.          |
| `title`  | string  | **Required**, not blank, up to 500 characters. Whitespace at either end is trimmed. |
| `author` | string  | **Required**, not blank, up to 500 characters. Whitespace at either end is trimmed. |
| `year`   | integer | Optional (`null`). From -9999 to next year; negative years are BCE.            |
| `isbn`   | string  | Optional (`null`). Must be an ISBN-10 or ISBN-13 (see below); an empty string counts as `null`. |

- **ISBN format:** 10 or 13 digits, optionally separated by single hyphens or
  spaces. An ISBN-10 may end in `X`. The check digit is not verified, and the
  value is stored exactly as sent.
- **Unknown fields** are ignored.
- **Invalid values:** the server reports every invalid field at once, in `details`.

### Behaviour notes

- `PUT` replaces the whole book, following HTTP semantics. It uses the same
  rules as `POST`: `title` and `author` are required, and an omitted `year` or
  `isbn` is cleared to `null`.
- `GET /books?author=...` returns books whose author contains the given text,
  ignoring case (Unicode-aware, so `GARCÍA` matches `García`). An empty filter
  returns every book.
- Books are listed in the order they were created (by `id`).
- Request bodies must be JSON objects of at most 1 MiB. An empty or malformed
  body gets a `400`, and a larger one gets a `413`.

### Error format

```json
{"error": "Book 42 not found"}
```

Validation failures also include a `details` object, keyed by field:

```json
{"error": "Validation failed",
 "details": {"title": "title is required", "author": "author is required"}}
```

### Examples

```bash
$ curl -s localhost:8000/health
{"status": "ok", "database": "ok"}

$ curl -s -X POST localhost:8000/books -H 'Content-Type: application/json' \
    -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}

$ curl -s -X POST localhost:8000/books -H 'Content-Type: application/json' \
    -d '{"title": "The Dispossessed", "author": "Ursula K. Le Guin", "year": 1974}'
{"id": 2, "title": "The Dispossessed", "author": "Ursula K. Le Guin", "year": 1974, "isbn": null}

$ curl -s 'localhost:8000/books?author=le%20guin'
[{"id": 2, "title": "The Dispossessed", "author": "Ursula K. Le Guin", "year": 1974, "isbn": null}]

$ curl -s localhost:8000/books/1
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}

$ curl -s -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
    -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": null}

$ curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8000/books/1
204

$ curl -s -X POST localhost:8000/books -H 'Content-Type: application/json' -d '{"year": 1965}'
{"error": "Validation failed", "details": {"title": "title is required", "author": "author is required"}}
```

## Tests

```bash
python -m pytest
```

There are 107 tests, and they run in about two seconds:

- `tests/test_validation.py`: the payload validation rules.
- `tests/test_repository.py`: the SQLite layer. Covers CRUD, the author
  filter, ids not being reused, persistence across connections, out-of-range
  ids, and concurrent writers.
- `tests/test_api.py`: every endpoint in-process, including status codes,
  error bodies, `405`/`Allow`, oversized and malformed bodies, `HEAD`, and
  `500` handling. Each request and response is also checked for WSGI
  compliance with `wsgiref.validate`.
- `tests/test_server.py`: end-to-end over real HTTP. Runs a full CRUD
  lifecycle and concurrent requests against the threaded server, then launches
  `python -m books_api` as a subprocess and checks it serves requests, writes
  to its database file, and exits cleanly on SIGINT and SIGTERM.

## Project layout

```
books_api/
  __main__.py     command-line entry point (python -m books_api)
  app.py          WSGI app: routing, JSON request/response handling, handlers
  models.py       Book and BookData dataclasses
  repository.py   SQLite storage (BookRepository)
  server.py       multi-threaded wsgiref server
  validation.py   payload validation rules
tests/            pytest suite (see above)
```

## Design notes

- **Standard library only.** No framework was specified. Using `wsgiref` and
  `sqlite3` means nothing needs installing to run the service, and keeping the
  app as a plain WSGI callable leaves it portable to other WSGI servers.
- **SQLite access.** All request threads share one connection, guarded by a
  lock. This is simple, correct, and lets `:memory:` databases work with the
  threaded server. Every write is committed immediately.
- **Stable ids.** The `id` column uses `AUTOINCREMENT`, so the URL of a deleted
  book never ends up pointing at a different book.
