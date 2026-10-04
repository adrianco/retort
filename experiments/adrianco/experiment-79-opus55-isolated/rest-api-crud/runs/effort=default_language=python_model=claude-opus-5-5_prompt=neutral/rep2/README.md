# Book Collection API

A REST API for managing a book collection, written in Python using only the
standard library (`wsgiref` for HTTP, `sqlite3` for storage). There is nothing
to install to run it.

## Requirements

- Python 3.11+ (developed on 3.14)
- `pytest`, only for running the tests

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db` in
the current directory. Both are configurable through environment variables:

| Variable   | Default     | Purpose                   |
|------------|-------------|---------------------------|
| `HOST`     | `127.0.0.1` | Address to bind           |
| `PORT`     | `8000`      | Port to listen on         |
| `BOOKS_DB` | `books.db`  | Path to the SQLite file   |

```bash
PORT=9000 BOOKS_DB=/tmp/books.db python app.py
```

## Test

```bash
python -m venv venv && source venv/bin/activate   # optional
pip install -r requirements-dev.txt
python -m pytest
```

The tests use a temporary database per test, and include one end-to-end test
that talks to a real server on an ephemeral port.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                          | Success | Errors        |
|--------|---------------|--------------------------------------|---------|---------------|
| GET    | `/health`     | Health check, returns `{"status": "ok"}` | 200 |               |
| POST   | `/books`      | Create a book                        | 201     | 400, 409      |
| GET    | `/books`      | List books, optional `?author=` filter | 200   |               |
| GET    | `/books/{id}` | Get one book                         | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404, 409 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 404           |

Validation rules:

- `title` and `author` are required, non-empty strings (surrounding whitespace
  is trimmed).
- `year` is optional and must be an integer.
- `isbn` is optional and must be a string. It must be unique when provided; a
  duplicate returns `409 Conflict`.
- `PUT` replaces the whole book, so it takes the same fields as `POST`;
  optional fields that are left out are reset to `null`.
- The `?author=` filter matches the whole author name, ignoring ASCII case.

Errors are JSON too. Validation failures list the offending fields:

```json
{"error": "Validation failed", "details": {"title": "title is required"}}
```

Other statuses: `400` for a body that isn't a JSON object, `404` for unknown
paths, `405` (with an `Allow` header) for unsupported methods, and `413` for
bodies over 1 MB.

### Examples

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'

curl -i -X DELETE localhost:8000/books/1
```

## Layout

- `app.py` — WSGI application: routing, validation, and the server entry point
- `db.py` — SQLite storage
- `test_app.py` — tests
