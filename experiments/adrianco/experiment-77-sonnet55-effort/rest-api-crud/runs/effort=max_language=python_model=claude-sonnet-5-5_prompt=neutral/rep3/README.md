# Book Collection API

A small REST API for managing a book collection. Books are stored in SQLite and every
response is JSON.

It has **no third-party runtime dependencies**. No web framework was specified, so it is a
plain [WSGI](https://peps.python.org/pep-3333/) application built on the Python standard
library (`sqlite3`, `json`, `wsgiref`): there is nothing to install to run it, and the
same application object can be served by any WSGI server.

| Method   | Path           | Description                                | Success          |
|----------|----------------|--------------------------------------------|------------------|
| `POST`   | `/books`       | Create a book                              | `201 Created`    |
| `GET`    | `/books`       | List all books (optional `?author=` filter) | `200 OK`         |
| `GET`    | `/books/{id}`  | Get one book                               | `200 OK`         |
| `PUT`    | `/books/{id}`  | Replace (update) a book                    | `200 OK`         |
| `DELETE` | `/books/{id}`  | Delete a book                              | `204 No Content` |
| `GET`    | `/health`      | Health check                               | `200 OK`         |

## Setup

Requires **Python 3.9 or newer**. The service itself needs nothing else; `pytest` is only
needed to run the tests.

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt     # pytest + pytest-cov, for the tests only
```

## Run

From the project root:

```bash
PYTHONPATH=src python -m bookapi
```

The API is now listening on <http://127.0.0.1:8000>. At start-up it creates `books.db` in
the current directory if that file does not exist yet. Stop it with `Ctrl+C`.

| Option        | Environment variable | Default        | Meaning                                      |
|---------------|----------------------|----------------|----------------------------------------------|
| `--host`      | `BOOKAPI_HOST`       | `127.0.0.1`    | IPv4 interface to listen on                  |
| `--port`      | `BOOKAPI_PORT`       | `8000`         | Port to listen on (`0` picks a free one)     |
| `--db`        | `BOOKAPI_DB`         | `books.db`     | SQLite file (created, with parent directories, if missing) |
| `--log-level` |                      | `INFO`         | `DEBUG`, `INFO`, `WARNING` or `ERROR`        |

An environment variable that is set but empty counts as unset, and an empty `--host` or
`--db` is rejected (an empty host would otherwise mean "every interface"). If the database
cannot be opened or the port is taken, the server says so and exits with status 1.

```bash
PYTHONPATH=src python -m bookapi --port 9000 --db data/library.db
```

Alternatively, `pip install -e .` puts a `bookapi` command on your path (taking the same
options) and makes `PYTHONPATH=src` unnecessary.

> **Security:** there is no authentication, and the default host only accepts local
> connections. Think twice before using `--host 0.0.0.0`.

## Using the API

```console
$ curl -s http://127.0.0.1:8000/health
{"status":"ok"}

$ curl -i -X POST http://127.0.0.1:8000/books \
       -H 'Content-Type: application/json' \
       -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}'
HTTP/1.0 201 Created
Content-Type: application/json; charset=utf-8
Location: /books/1

{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}

$ curl -s http://127.0.0.1:8000/books
[{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"},
 {"id":2,"title":"Emma","author":"Jane Austen","year":1815,"isbn":null},
 {"id":3,"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":null}]

$ curl -s 'http://127.0.0.1:8000/books?author=frank%20herbert'
[{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"},
 {"id":3,"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":null}]

$ curl -s http://127.0.0.1:8000/books/2
{"id":2,"title":"Emma","author":"Jane Austen","year":1815,"isbn":null}

$ curl -s -X PUT http://127.0.0.1:8000/books/2 \
       -H 'Content-Type: application/json' \
       -d '{"title": "Emma", "author": "Jane Austen", "year": 1816, "isbn": "978-0-14-143958-7"}'
{"id":2,"title":"Emma","author":"Jane Austen","year":1816,"isbn":"978-0-14-143958-7"}

$ curl -i -X DELETE http://127.0.0.1:8000/books/3
HTTP/1.0 204 No Content

$ curl -s http://127.0.0.1:8000/books/3
{"error":"Book 3 not found"}

$ curl -s -X POST http://127.0.0.1:8000/books -H 'Content-Type: application/json' \
       -d '{"title": "", "year": "soon"}'
{"error":"Validation failed","details":{"title":"must not be blank","author":"is required","year":"must be an integer"}}
```

(Bodies are shown wrapped for readability; the server sends compact JSON.)

## API reference

### The book resource

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
```

| Field    | Type    | Required | Rules                                                                 |
|----------|---------|----------|-----------------------------------------------------------------------|
| `id`     | integer | –        | Assigned by the server, starting at 1. Never reused after a delete. Ignored if sent. |
| `title`  | string  | **yes**  | Not blank, at most 255 characters.                                    |
| `author` | string  | **yes**  | Not blank, at most 255 characters.                                    |
| `year`   | integer | no       | A JSON integer from 1 to 9999. `null`/absent means unknown.           |
| `isbn`   | string  | no       | At most 32 characters; not checked for structure. Blank means unknown. |

Text is trimmed of surrounding whitespace before it is validated and stored, and may not
contain control characters (including newlines). Unknown JSON keys are ignored.

### Endpoints

- **`POST /books`** – body: a JSON object with the fields above. Responds `201` with the
  created book and a `Location: /books/{id}` header.
- **`GET /books`** – responds `200` with a JSON array of books in creation order (`[]` when
  there are none). `?author=Name` keeps only books by that author: an exact match that
  ignores case, not a substring search. A blank `?author=` filters nothing.
- **`GET /books/{id}`** – responds `200` with the book, or `404`.
- **`PUT /books/{id}`** – **replaces** the whole book, so it is validated exactly like
  `POST` (`title` and `author` are required) and any omitted optional field (`year`, `isbn`)
  is cleared. Responds `200` with the updated book, or `404`.
- **`DELETE /books/{id}`** – responds `204` with no body, or `404`.
- **`GET /health`** – `200 {"status":"ok"}` while the `books` table can be read, otherwise
  `503 {"status":"unavailable","error":"Database unavailable"}`.

`HEAD` works wherever `GET` does. Trailing slashes are accepted, and a book has exactly one
URL (`/books/7`, not `/books/007`). Request bodies are always parsed as JSON, whatever their
`Content-Type`; they may be at most 64 KiB and must be sent with a `Content-Length` header.

### Status codes and errors

| Status | When                                                                                   |
|--------|----------------------------------------------------------------------------------------|
| `200`  | Successful `GET` or `PUT`                                                              |
| `201`  | Book created                                                                           |
| `204`  | Book deleted                                                                           |
| `400`  | Invalid JSON, a body that is not a JSON object, a bad `Content-Length`, or a book that fails validation |
| `404`  | Unknown book id (including ids that are not numbers) or unknown path                  |
| `405`  | Known path, unsupported method (an `Allow` header lists the valid ones)                |
| `408`  | The client stopped sending before the whole body (as promised by `Content-Length`) arrived |
| `411`  | A body sent without `Content-Length` (chunked uploads are not supported)               |
| `413`  | Request body larger than 64 KiB                                                        |
| `500`  | Unexpected error; the body is generic and the details are only logged                  |
| `503`  | `/health` cannot read the database                                                     |

Every error the application produces is JSON of the form `{"error": "..."}`. (Malformed
HTTP that the bundled server rejects before the application runs, such as an over-long
request line, gets the server's own plain error page.) Validation errors (`400`) add a
`details` object that names **every** invalid field, so a client can fix them all at once:

```json
{"error": "Validation failed", "details": {"title": "is required", "year": "must be an integer"}}
```

## Tests

```bash
python -m pytest                                           # the whole suite takes a few seconds
python -m pytest --cov=bookapi --cov-report=term-missing   # with line + branch coverage
```

| File                       | What it covers                                                              |
|----------------------------|-----------------------------------------------------------------------------|
| `tests/test_validation.py` | Unit tests for every validation rule                                        |
| `tests/test_repository.py` | SQLite layer: CRUD, author filter, persistence, id edge cases, thread safety, corrupt files |
| `tests/test_api.py`        | Every endpoint and status code, plus hostile input, driven in-process through the WSGI interface (each call is also checked against the PEP 3333 validator) |
| `tests/test_server.py`     | Real HTTP over a loopback socket: full CRUD lifecycle, restart persistence, concurrent clients, stalled and malformed clients, log escaping, the CLI, and `python -m bookapi` itself |

The tests never touch `books.db`: they use in-memory databases or pytest's temporary
directories. If a sandbox forbids loopback sockets, the socket-based tests skip rather than fail.

## Project layout

```
src/bookapi/
  app.py          WSGI application: routing and the endpoint handlers
  web.py          Request/response helpers (JSON parsing, body limits, error responses)
  validation.py   Book payload validation and normalisation
  repository.py   SQLite storage (schema, CRUD, case-insensitive author search)
  server.py       Threaded wsgiref server and the command-line interface
tests/            The test suite described above
pyproject.toml    Package metadata and pytest/coverage settings
requirements.txt  Test-only dependencies
```

## Design notes

- **Storage.** One SQLite connection is shared by all server threads behind a lock. That is
  plenty for SQLite, which serialises writers anyway, and it lets `:memory:` databases work.
  All SQL uses bound parameters. The schema also refuses blank titles and authors, as a
  second line of defence behind the validation layer.
- **Ids** use `AUTOINCREMENT`, so the id of a deleted book is never handed to a new one.
  Ids too large for SQLite (or otherwise impossible) are simply "not found", not errors.
- **Hardening.** Untrusted input is bounded everywhere it enters: body size and
  `Content-Length` are checked before anything is read or parsed, JSON that is malformed,
  contains `NaN`, or nests deeper than the interpreter can parse is a `400` and never a
  crash, connections that stall are dropped after 30 seconds, and control characters in a
  request line are escaped before they reach the log.
- **`PUT` is a full replacement** (as HTTP defines it), not a partial update. Fetch the
  book, change what you need, and send it all back.
- **The bundled server** (`wsgiref`, one thread per request) is meant for local use and
  small deployments. Because the application is a plain WSGI callable, a production server
  can serve it instead. For example, with `pip install gunicorn`, run from the project root:

  ```bash
  gunicorn --pythonpath src 'bookapi:create_app()' -b 127.0.0.1:8000
  ```

  This keeps the database in `books.db` in the working directory; to use another file,
  call `create_app("path/to/library.db")` from your own small WSGI module.

## Limitations

- There is no authentication, pagination, or CORS support.
- The bundled server speaks HTTP/1.0 over IPv4 only: one request per connection, no
  keep-alive, no `Expect: 100-continue` (a client that sends it waits about a second) and no
  chunked request bodies. A client that keeps streaming a body far larger than 64 KiB may see
  its connection reset instead of reading the `413`.
- `isbn` is stored as given, and a title or author made only of invisible characters (such
  as a zero-width space) still counts as non-blank.
