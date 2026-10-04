# Book Collection API

A small REST service for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so there is nothing to install to
run it. `pytest` is needed only for the tests.

## Requirements

- Python 3.9+
- `pytest` (tests only)

## Run

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db` in
the current directory. Configure it with environment variables:

| Variable   | Default     | Meaning                                  |
|------------|-------------|------------------------------------------|
| `HOST`     | `127.0.0.1` | Address to bind                          |
| `PORT`     | `8000`      | Port to listen on                        |
| `BOOKS_DB` | `books.db`  | SQLite file (`:memory:` for a throwaway) |

```bash
PORT=9000 BOOKS_DB=/tmp/books.db python3 app.py
```

## Test

```bash
python3 -m venv venv              # skip if venv/ already exists
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest
```

The tests start the real server on a free port with a temporary database and
talk to it over HTTP.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Success          | Errors     |
|--------|---------------|------------------|------------|
| GET    | `/health`     | 200 `{"status": "ok"}` |      |
| POST   | `/books`      | 201 + the book, `Location` header | 400 |
| GET    | `/books`      | 200 + array of books |        |
| GET    | `/books/{id}` | 200 + the book   | 404        |
| PUT    | `/books/{id}` | 200 + the book   | 400, 404   |
| DELETE | `/books/{id}` | 204, no body     | 404        |

Unknown paths return 404 and unsupported methods return 405 with an `Allow`
header.

### Fields and validation

| Field    | Type    | Required | Notes                         |
|----------|---------|----------|-------------------------------|
| `title`  | string  | yes      | must not be blank             |
| `author` | string  | yes      | must not be blank             |
| `year`   | integer | no       | `null` when omitted           |
| `isbn`   | string  | no       | `null` when omitted; not checked for format or uniqueness |

Strings are trimmed of surrounding whitespace. Unknown fields, including `id`,
are ignored.

`PUT` replaces the whole book: `title` and `author` are required again, and an
omitted `year` or `isbn` is reset to `null`.

`GET /books?author=Frank%20Herbert` returns only books whose author matches the
whole name, ignoring ASCII case.

### Errors

Every error is JSON with an `error` message. Validation failures (400) also
list each offending field:

```json
{"error": "Validation failed", "details": {"title": "is required", "year": "must be an integer"}}
```

Malformed JSON returns 400, and a body over 1 MB returns 413.

### Example

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'

curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```
