# Book Collection API

A small REST API for managing a collection of books, written in Python with **no third-party
runtime dependencies**: a WSGI application served by the standard library, storing data in
SQLite.

- `POST /books`, `GET /books` (with `?author=` filter), `GET /books/{id}`, `PUT /books/{id}`,
  `DELETE /books/{id}` and `GET /health`
- JSON in, JSON out, with meaningful HTTP status codes and per-field validation errors
- 250+ automated tests (unit, WSGI-level integration, and real-socket end-to-end)

## Requirements

- Python 3.9 or newer (the test suite passes on 3.9, 3.11 and 3.14)
- Nothing else to run the service. `pytest` (and optionally `pytest-cov`) is only needed to run
  the tests.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt     # test tooling only; the service itself needs no packages
```

## Run

```bash
PYTHONPATH=src python -m bookapi
```

The API is now listening on <http://127.0.0.1:8000> and stores its data in `./books.db`
(created on first start). Stop it with Ctrl+C (or `kill`; SIGTERM shuts down cleanly too).

If you prefer not to set `PYTHONPATH`, install the package once and run it from anywhere:

```bash
pip install -e .
bookapi --port 5000 --db shelf.db                       # or: python -m bookapi ...
```

| Option   | Environment variable | Default        | Meaning                                              |
|----------|----------------------|----------------|------------------------------------------------------|
| `--host` | `BOOKS_HOST`         | `127.0.0.1`    | Interface to listen on (`0.0.0.0` = all interfaces)  |
| `--port` | `BOOKS_PORT`         | `8000`         | Port to listen on (`0` picks a free one)             |
| `--db`   | `BOOKS_DB`           | `books.db`     | SQLite database file, created if it does not exist   |

Flags override environment variables, which override the defaults. The server only listens on
the loopback interface unless you ask otherwise.

## API

All request and response bodies are JSON (`application/json`), and so is every error, even one
raised by the HTTP layer itself (say, a malformed request line). A request with a body must
carry a `Content-Length` header, as every ordinary client sends; chunked uploads get a `411`.

| Method   | Path            | Description                     | Success                       | Errors             |
|----------|-----------------|---------------------------------|-------------------------------|--------------------|
| `POST`   | `/books`        | Create a book                   | `201` + book, `Location` header | `400`, `413`     |
| `GET`    | `/books`        | List books (optional `?author=`) | `200` + array of books       | `400`              |
| `GET`    | `/books/{id}`   | Get one book                    | `200` + book                  | `404`              |
| `PUT`    | `/books/{id}`   | Replace a book                  | `200` + updated book          | `400`, `404`, `413` |
| `DELETE` | `/books/{id}`   | Delete a book                   | `204` (no body)               | `404`              |
| `GET`    | `/health`       | Health check (verifies the database) | `200` `{"status": "ok"}` | `503`              |

`HEAD` and `OPTIONS` work on every route, and a trailing slash is ignored (`/books/` is
`/books`).

### The book object

```json
{"id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
```

| Field    | Type    | Required | Rules                                                                 |
|----------|---------|----------|-----------------------------------------------------------------------|
| `id`     | integer | –        | Assigned by the server; ignored if sent. Ids are never reused.         |
| `title`  | string  | **yes**  | Not blank after trimming; at most 500 characters                       |
| `author` | string  | **yes**  | Not blank after trimming; at most 255 characters                       |
| `year`   | integer | no       | 1 to next calendar year. `null` or omitted means unknown               |
| `isbn`   | string  | no       | At most 32 characters; blank means `null`. The format is not checked   |

Text is trimmed before it is stored, and unknown fields are ignored. The body must be a JSON
object of at most 1 MiB; a `Content-Type` header is not required.

`PUT` is a **full replacement** (as HTTP defines it): `title` and `author` are required again,
and an omitted `year` or `isbn` is cleared. There is deliberately no `PATCH`.

### Filtering

`GET /books?author=George%20Orwell` returns only books whose author matches **exactly**, ignoring
case and surrounding whitespace (Unicode-aware, so `?author=GABRIEL GARCÍA MÁRQUEZ` finds
"Gabriel García Márquez"). It is a filter, not a search: `?author=Orwell` does not match
"George Orwell". A blank `?author=` means no filter, and repeating the parameter is a `400`.
Books are always returned in id order.

### Errors

Every error has the same shape: a human-readable `error`, plus `details` (field → message) for
validation failures.

| Status | When                                                                              |
|--------|-----------------------------------------------------------------------------------|
| `400`  | Invalid JSON, body is not a JSON object, failed validation, repeated `author`      |
| `404`  | Unknown book, an id that cannot exist (`abc`, `0`, `-1`, `007`…), or unknown path    |
| `405`  | Known path, wrong method; the `Allow` header lists the right ones                  |
| `408`  | The request body did not arrive in time                                            |
| `411`  | The body was sent with chunked transfer encoding instead of a `Content-Length`     |
| `413`  | Request body larger than 1 MiB                                                    |
| `500`  | Unexpected failure: a generic message is returned, the details go to the server log |
| `503`  | `/health` only: the database is not reachable                                      |

### Examples

```console
$ curl -s -X POST localhost:8000/books -H 'Content-Type: application/json' \
       -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
{"id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}      # 201, Location: /books/1

$ curl -s -X POST localhost:8000/books -d '{"title": "Animal Farm", "author": "George Orwell"}'
{"id": 2, "title": "Animal Farm", "author": "George Orwell", "year": null, "isbn": null}                           # 201

$ curl -s -X POST localhost:8000/books -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
{"id": 3, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": null}                                 # 201

$ curl -s 'localhost:8000/books?author=george%20orwell'
[{"id": 1, "title": "Nineteen Eighty-Four", ...}, {"id": 2, "title": "Animal Farm", ...}]                          # 200

$ curl -s localhost:8000/books/1
{"id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}      # 200

$ curl -s -X PUT localhost:8000/books/2 -d '{"title": "Animal Farm", "author": "George Orwell", "year": 1945}'
{"id": 2, "title": "Animal Farm", "author": "George Orwell", "year": 1945, "isbn": null}                           # 200

$ curl -s -X DELETE localhost:8000/books/3                                                                       # 204, no body

$ curl -s localhost:8000/books/3
{"error": "Book not found"}                                                                                      # 404

$ curl -s -X POST localhost:8000/books -d '{"author": "  ", "year": "soon"}'
{"error": "Validation failed", "details": {"title": "title is required", "author": "author must not be blank", "year": "year must be an integer"}}     # 400

$ curl -s localhost:8000/health
{"status": "ok"}                                                                                                 # 200
```

## Tests

```bash
pytest                                              # everything, ~1 second
pytest --cov=bookapi --cov-report=term-missing      # with coverage (needs pytest-cov)
```

The suite lives in `tests/` and has four layers:

| File                     | What it covers                                                                  |
|--------------------------|---------------------------------------------------------------------------------|
| `test_validation.py`     | The validation rules in isolation: types, bounds, trimming, every error message  |
| `test_repository.py`     | The SQLite layer: CRUD, case-insensitive filter, id limits, persistence, threads |
| `test_api.py`            | Every endpoint and error path through the WSGI interface, with no sockets. The app is wrapped in `wsgiref.validate`, so each test also checks PEP 3333 conformance |
| `test_server.py`         | A real server on a loopback socket: full lifecycle, concurrent clients, stalled and malformed requests, log escaping, restart persistence, the CLI, and a `python -m bookapi` subprocess |

No test uses a fixed port or a fixed file path; databases are in-memory or in pytest's temp
directory.

## Project layout

```
src/bookapi/
    models.py        Book and BookData dataclasses
    validation.py    payload validation and normalisation (no HTTP, no SQL)
    repository.py    SQLite storage: one thread-safe class
    web.py           request parsing, JSON responses, HTTP errors (WSGI helpers)
    app.py           routing and the endpoint handlers (the WSGI application)
    server.py        threaded server and the command-line entry point
tests/               the test suite described above
pyproject.toml       packaging, pytest and lint configuration
requirements.txt     test tooling
```

## Design notes

- **Standard library only.** No framework was specified, so the service is a plain WSGI
  application (PEP 3333) on top of `wsgiref` and `sqlite3`: nothing to install, and the same
  callable runs under any WSGI server (see below).
- **One shared SQLite connection, guarded by a lock.** This keeps in-memory databases working and
  is plenty for SQLite, which serialises writers anyway. Do not remove the lock: the
  case-insensitive author filter is a Python function called from inside SQL, and using one
  connection from several threads without serialising access deadlocks the whole interpreter
  (reproduced while testing; `test_repository.py` and `test_api.py` cover it).
- **Validation happens before storage**, and the database repeats the essentials
  (`NOT NULL`, non-blank text) as a safety net.
- **The API never returns a stack trace.** Unexpected errors are logged with their traceback and
  reported as a generic `500`.

## Running beyond development

The built-in server is `wsgiref` with a thread per request: fine for development and small
internal use. For anything heavier, run the same application under a production WSGI server.
`create_app()` builds it, reading the database path from `BOOKS_DB`:

```bash
pip install gunicorn
BOOKS_DB=/var/lib/books/shelf.db gunicorn --bind 0.0.0.0:8000 'bookapi:create_app()'
```

There is no authentication, TLS or rate limiting; put the service behind a reverse proxy if it
is exposed beyond a trusted network.

## Limitations

- No pagination: `GET /books` returns the whole collection.
- ISBNs are stored as given; their format and check digit are not validated.
- The author filter scans the table, which is fine for personal-sized collections.
