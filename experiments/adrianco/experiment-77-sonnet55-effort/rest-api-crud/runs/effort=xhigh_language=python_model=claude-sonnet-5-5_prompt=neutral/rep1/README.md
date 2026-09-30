# Book Collection API

A small REST API for managing a collection of books. It is a plain WSGI application
backed by SQLite, written against the Python standard library only — there are **no
runtime dependencies** to install.

## Requirements

- Python 3.10 or newer (developed and tested on 3.14)
- `pytest` to run the tests (optional)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest        # only needed for the tests
```

The service itself needs nothing installed. Optionally, `pip install .` installs the
package and a `bookapi` console command.

## Run

From the repository root:

```bash
PYTHONPATH=src python -m bookapi                     # http://127.0.0.1:8000, DB: ./books.db
PYTHONPATH=src python -m bookapi --port 9000 --db /tmp/books.db
```

(If you ran `pip install .`, use `bookapi --port 9000` instead and drop `PYTHONPATH`.)

| Option   | Environment variable | Default     |
|----------|----------------------|-------------|
| `--host` | `HOST`               | `127.0.0.1` |
| `--port` | `PORT`               | `8000`      |
| `--db`   | `BOOKS_DB_PATH`      | `books.db`  |

The database file and `books` table are created on first start. The bundled server
(`wsgiref`, threaded) is meant for development; the app is a standard WSGI callable
(`bookapi.create_app(db_path)`), but it has only been tested with the bundled server.

## API

All request and response bodies are JSON. Errors look like
`{"error": "message"}`, with `"details": {"<field>": "<problem>"}` added for
validation failures.

| Method | Path           | Success                  | Errors                          |
|--------|----------------|--------------------------|---------------------------------|
| GET    | `/health`      | `200 {"status": "ok"}`   | `503` if the database is unusable |
| POST   | `/books`       | `201` + book, `Location` header | `400`, `413`             |
| GET    | `/books`       | `200` list of books      |                                 |
| GET    | `/books/{id}`  | `200` book               | `404`                           |
| PUT    | `/books/{id}`  | `200` updated book       | `400`, `404`, `413`             |
| DELETE | `/books/{id}`  | `204` no content         | `404`                           |

Other paths return `404`; unsupported methods return `405` with an `Allow` header.

### Book object

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Field    | Rules                                                                   |
|----------|-------------------------------------------------------------------------|
| `title`  | **required**, string, non-blank, at most 255 characters (trimmed)       |
| `author` | **required**, string, non-blank, at most 255 characters (trimmed)       |
| `year`   | optional integer 0–9999 (`null` allowed)                                |
| `isbn`   | optional string, at most 32 characters; a blank string is stored as `null`. The format is not checked. |

Unknown fields are ignored. `id` is assigned by the server and is never reused.

### Behaviour notes

- **`GET /books?author=NAME`** returns books whose author equals `NAME` exactly,
  ignoring case (Unicode-aware). It is not a substring search. A blank `author=`
  is treated as no filter. Results are ordered by `id`.
- **`PUT /books/{id}`** applies the fields you send and keeps the rest, so
  `{"year": 1966}` is a valid update. Sending `null` for `year` or `isbn` clears
  them. Every supplied field is validated, and an empty body (or one with no
  recognised fields) is a `400`. A missing book is a `404` even if the body is
  also invalid.
- A `{id}` that is not a positive integer can never match a book, so it returns `404`.
- Request bodies over 1 MB are rejected with `413`.

### Examples

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -d '{"year": 1966}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health

# validation failure
curl -X POST localhost:8000/books -d '{"title": ""}'
# -> 400 {"error": "Validation failed", "details": {"title": "title must not be empty", "author": "author is required"}}
```

## Tests

```bash
pytest                                   # from the repository root
pytest --cov=bookapi --cov-report=term-missing   # needs pytest-cov
```

`pyproject.toml` puts `src/` on the path, so no install is needed. The suite covers:

- `tests/test_api.py` — every endpoint, status codes, filtering, validation and error cases,
  called directly through the WSGI interface with an in-memory database
- `tests/test_validation.py` — the validation rules in isolation
- `tests/test_repository.py` — the SQLite layer, persistence to a file, and concurrent writes
- `tests/test_server.py` — real HTTP requests against the bundled server, including a
  subprocess launch of `python -m bookapi`

## Layout

```
src/bookapi/
  app.py         WSGI app: routing, request parsing, handlers, error mapping
  db.py          BookRepository (SQLite, thread-safe)
  validation.py  payload validation
  __main__.py    command-line entry point
tests/           pytest suite
```
