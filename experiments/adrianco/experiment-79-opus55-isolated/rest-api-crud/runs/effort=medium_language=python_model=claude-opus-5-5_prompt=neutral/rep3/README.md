# Book Collection API

A small REST API for managing a book collection, written in Python and backed by
SQLite. It uses only the standard library (`wsgiref` + `sqlite3`), so there is
nothing to install to run it; `pytest` is needed only for the tests.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```bash
python app.py                          # http://127.0.0.1:8000, data in ./books.db
python app.py --host 0.0.0.0 --port 9000 --db /path/to/books.db
```

The `HOST`, `PORT` and `BOOKS_DB` environment variables set the same options.
The bundled `wsgiref` server is intended for local use; `create_app()` returns a
standard WSGI app that can be hosted by any WSGI server.

## Test

```bash
python -m pytest
```

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                          | Success | Errors        |
|--------|---------------|--------------------------------------|---------|---------------|
| GET    | `/health`     | Health check, `{"status": "ok"}`     | 200     |               |
| POST   | `/books`      | Create a book                        | 201     | 400, 409, 413 |
| GET    | `/books`      | List books; `?author=` filters       | 200     |               |
| GET    | `/books/{id}` | Get one book                         | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404, 409 |
| DELETE | `/books/{id}` | Delete a book (empty response body)  | 204     | 404           |

Unknown paths return 404 and unsupported methods return 405 with an `Allow` header.

### Validation

- `title` and `author` are required, non-empty strings (surrounding whitespace is trimmed).
- `year` is optional; if given it must be an integer between -9999 and 9999.
- `isbn` is optional; if given it must be a non-empty string, and it must be
  unique across books (a duplicate returns 409).
- `PUT` is a full replacement: omitted `year`/`isbn` are reset to `null`.
- `?author=` matches the whole author name, case-insensitively.
- Unknown fields in the request body are ignored.

Errors are JSON, with per-field details for validation failures:

```json
{"error": "Validation failed", "details": {"title": "title is required"}}
```

### Example

```bash
curl -X POST localhost:8000/books \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1
```
