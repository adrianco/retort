# Book Collection API

A small REST API for managing a collection of books. It speaks JSON over HTTP and
stores its data in SQLite.

It is written in Python using **only the standard library** (`wsgiref`, `sqlite3`,
`json`), so there is nothing to install in order to run it.

| Method   | Path           | Purpose                                     |
| -------- | -------------- | ------------------------------------------- |
| `POST`   | `/books`       | Create a book                               |
| `GET`    | `/books`       | List books (optional `?author=` filter)     |
| `GET`    | `/books/{id}`  | Get one book                                |
| `PUT`    | `/books/{id}`  | Update (replace) a book                     |
| `DELETE` | `/books/{id}`  | Delete a book                               |
| `GET`    | `/health`      | Health check                                |

## Requirements

- Python 3.9 or newer (the test suite passes on 3.9, 3.11 and 3.14).
- `pytest` and `pytest-cov`, **only** to run the tests (`requirements.txt`).

## Setup

The commands below are for a POSIX shell (developed and tested on macOS).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt     # test tooling only; the service has no dependencies
```

## Run

From the project root:

```bash
PYTHONPATH=src python -m bookapi
```

The server listens on <http://127.0.0.1:8000> and creates `books.db` in the current
directory on first start. Stop it with `Ctrl+C`.

Alternatively, install the package and use the `bookapi` command from anywhere:

```bash
pip install -e .
bookapi
```

Options (each also has an environment variable, which counts as unset if empty; a
command-line flag wins):

| Flag     | Environment variable | Default     | Meaning                                  |
| -------- | -------------------- | ----------- | ---------------------------------------- |
| `--host` | `BOOKS_HOST`         | `127.0.0.1` | Address to listen on (`0.0.0.0` = all)   |
| `--port` | `BOOKS_PORT`         | `8000`      | Port to listen on (`0` picks a free one) |
| `--db`   | `BOOKS_DB`           | `books.db`  | SQLite file, created if it does not exist |

```bash
PYTHONPATH=src python -m bookapi --port 9000 --db /tmp/library.db
```

Check that it is up:

```bash
curl http://127.0.0.1:8000/health
# {"status": "ok"}
```

## API

All request and response bodies are JSON. Successful responses carry the book(s)
directly; errors always look like `{"error": "..."}` (see [Errors](#errors)).

### The book object

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Field    | Type    | Required | Rules                                                      |
| -------- | ------- | -------- | ---------------------------------------------------------- |
| `id`     | integer | -        | Assigned by the server; never reused, even after a delete  |
| `title`  | string  | **yes**  | Not blank, at most 255 characters                          |
| `author` | string  | **yes**  | Not blank, at most 255 characters                          |
| `year`   | integer | no       | 1 to 9999. `null` if not given                             |
| `isbn`   | string  | no       | At most 32 characters, stored as given. `null` if not given |

Text is trimmed of leading/trailing whitespace and may not contain control
characters. Unknown fields in a request (such as an `id` echoed back by a client)
are ignored.

### Create a book: `POST /books`

```bash
curl -X POST http://127.0.0.1:8000/books \
     -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
```

`201 Created`, with a `Location: /books/1` header:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

### List books: `GET /books`

```bash
curl http://127.0.0.1:8000/books
```

`200 OK`: a JSON array, oldest first (empty if there are no books):

```json
[{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
 {"id": 2, "title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": null}]
```

Filter by author with `?author=`:

```bash
curl 'http://127.0.0.1:8000/books?author=frank%20herbert'
```

```json
[{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}]
```

The author must match **in full**, but upper/lower case is ignored, including for
non-ASCII letters (`É` matches `é`), and so is the way an accent is encoded (`ë` as one
character or as `e` plus a combining mark). `?author=Herbert` does not find
`Frank Herbert`. A blank `?author=` is the same as no filter, and an author with no
books gives `[]`. Non-ASCII names should be percent-encoded, as browsers and HTTP
libraries do; the built-in server also accepts them raw, as `curl` sends them.

### Get one book: `GET /books/{id}`

```bash
curl http://127.0.0.1:8000/books/1
```

`200 OK` with the book, or `404 Not Found` (`{"error": "Book not found"}`).

### Update a book: `PUT /books/{id}`

`PUT` **replaces** the whole book, so send every field you want to keep: `title` and
`author` are required as for `POST`, and an omitted `year` or `isbn` is cleared
(set to `null`).

```bash
curl -X PUT http://127.0.0.1:8000/books/1 \
     -H 'Content-Type: application/json' \
     -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966, "isbn": "9780441172719"}'
```

`200 OK` with the updated book. `404` if the id does not exist (`PUT` never
creates a book), `400` if the body is invalid (the stored book is left unchanged).

### Delete a book: `DELETE /books/{id}`

```bash
curl -X DELETE http://127.0.0.1:8000/books/1
```

`204 No Content` with an empty body, or `404` if the id does not exist.

### Health check: `GET /health`

`200 OK` with `{"status": "ok"}` when the service can reach its database, otherwise
`503 Service Unavailable` with `{"status": "unavailable"}`.

### Errors

Every error is a JSON object with an `error` message (only the health check's `503`
uses its own `{"status": ...}` shape). Validation errors also list every offending
field under `details`, so a client can fix them all in one go:

```bash
curl -X POST http://127.0.0.1:8000/books \
     -H 'Content-Type: application/json' \
     -d '{"author": "", "year": "1999"}'
```

`400 Bad Request`:

```json
{"error": "Validation failed: title is required; author is required; year must be an integer",
 "details": {"title": "title is required", "author": "author is required", "year": "year must be an integer"}}
```

| Status | When                                                                            |
| ------ | ------------------------------------------------------------------------------- |
| `400`  | Validation failed; body missing, not valid JSON, or not a JSON object; bad `Content-Length` |
| `404`  | No such book, or no such path (`/books/abc` is simply a path that does not exist) |
| `405`  | Wrong method for the path; the `Allow` header lists the right ones              |
| `408`  | The request body stalled or the connection dropped before it was fully received |
| `411`  | A body sent with `Transfer-Encoding: chunked`; send a `Content-Length` instead  |
| `413`  | Request body larger than 64 KiB                                                 |
| `500`  | Unexpected failure: a generic message is returned, details go to the server log |

Also worth knowing:

- A trailing slash is accepted (`/books/` = `/books`), and `HEAD` works wherever `GET`
  does.
- The `Content-Type` request header is not enforced, so a plain `curl -d '{...}'`
  works.
- The built-in server drops a client that goes silent for 30 seconds. A client that
  keeps uploading megabytes after a `413` may see the connection reset instead of the
  `413` itself, because the body is refused without being read.
- The same JSON error format is used for failures the built-in server detects before
  the application sees the request (a malformed request line, for instance). Under
  another WSGI server those responses are that server's own.

## Tests

```bash
python -m pytest                                             # run everything
python -m pytest --cov=bookapi --cov-report=term-missing     # ...with coverage
```

`pytest` alone also works, and no installation is needed: `pyproject.toml` puts
`src/` on the import path. The suite has more than 300 tests and takes a couple of
seconds.

| File                       | What it covers                                                      |
| -------------------------- | ------------------------------------------------------------------- |
| `tests/test_validation.py` | Unit tests for every validation rule, including boundaries          |
| `tests/test_repository.py` | SQLite storage: CRUD, author filter, id rules, persistence, threads |
| `tests/test_api.py`        | Integration tests of every endpoint through the WSGI interface      |
| `tests/test_server.py`     | Real HTTP over sockets, concurrent clients, the CLI, `python -m bookapi` in a subprocess |

The API tests call the app in-process (no sockets) through a small client that also
checks every request and response against the WSGI spec with `wsgiref.validate`.
Tests use in-memory databases, or temporary files for the ones that go through real
sockets; nothing is written to the project directory, and every server the tests
start uses a free port.

## Project layout

```
src/bookapi/
    models.py       Book and BookInput dataclasses
    validation.py   Validates and normalises request payloads
    repository.py   SQLite storage (the only module that knows about SQL)
    web.py          Request/Response helpers: body parsing, size limit, JSON output
    app.py          The WSGI application: routing and the endpoint handlers
    server.py       Command-line entry point and threaded development server
    __main__.py     Enables `python -m bookapi`
tests/              See above
pyproject.toml      Package metadata and pytest/coverage settings
requirements.txt    Test tooling (the service itself has no dependencies)
```

## Design notes

- **No framework.** The task did not name one, so the standard library is used. The
  application is a plain WSGI callable (`bookapi.app.BookApp`), which keeps it
  dependency-free and portable.
- **Serving.** `python -m bookapi` uses the standard library's `wsgiref` server with
  one thread per connection. That is fine for development and light use, but it has
  no limit on the number of connections and only a coarse idle timeout. For anything
  exposed to a network, run the same app under a production WSGI server via the
  `create_app` factory (it reads the database path from `BOOKS_DB`). The package must
  be importable, so `pip install .` first (or set `PYTHONPATH=src`). Both of these
  were tried (waitress 3.0.2, gunicorn 26.2.0) and work, including two gunicorn
  workers sharing one SQLite file:

  ```bash
  BOOKS_DB=/var/lib/books/books.db waitress-serve --call bookapi.app:create_app
  BOOKS_DB=/var/lib/books/books.db gunicorn 'bookapi.app:create_app()'
  ```
- **No authentication.** Anyone who can reach the port can read and change the data,
  which is why the server listens on `127.0.0.1` by default. Put authentication in
  front of it before using `--host 0.0.0.0` or any other public address. Even on
  `127.0.0.1`, a web page open in a browser on the same machine can send a
  cross-site `POST` (the `Content-Type` is not enforced, see above) and so add
  books; it cannot read the data back, and `PUT` and `DELETE` are blocked by the
  browser's CORS pre-flight.
- **Storage.** One SQLite connection per process, guarded by a lock. Every operation
  is a single parameterised statement, so it is atomic and immune to SQL injection.
  Ids use `AUTOINCREMENT`, so an id is never handed out twice.
- **ISBNs are not policed.** Only `title` and `author` are required by the spec, and
  ISBNs in the wild are inconsistent (hyphens, ISBN-10 vs ISBN-13, bad checksums),
  so any string up to 32 characters is stored as given. Nor are they required to be
  unique.
