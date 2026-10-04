# Book Collection API

A small REST API for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so there is nothing to install to
run it. No framework was specified for this task, so none was added.

## Requirements

- Python 3.9+
- `pytest` (tests only): `pip install -r requirements-dev.txt`

## Run

```bash
python3 app.py
```

Configuration is via environment variables:

| Variable   | Default     | Purpose                   |
|------------|-------------|---------------------------|
| `HOST`     | `127.0.0.1` | Bind address              |
| `PORT`     | `8000`      | Listen port               |
| `BOOKS_DB` | `books.db`  | SQLite database file path |

## Test

```bash
python3 -m pytest
```

The tests start the real server on an ephemeral port with a temporary database.

## API

A book has `id`, `title` (required), `author` (required), `year` (optional
integer) and `isbn` (optional string).

| Method | Path          | Success | Notes                                         |
|--------|---------------|---------|-----------------------------------------------|
| GET    | `/health`     | 200     | `{"status": "ok"}`                            |
| POST   | `/books`      | 201     | Returns the created book                      |
| GET    | `/books`      | 200     | `?author=` filters by exact author, case-insensitive |
| GET    | `/books/{id}` | 200     |                                               |
| PUT    | `/books/{id}` | 200     | Full replacement; omitted optional fields become `null` |
| DELETE | `/books/{id}` | 204     | Empty body                                    |

Errors are JSON: `{"error": "...", "details": {"field": "reason"}}` (`details`
only on validation failures). Status codes: `400` invalid JSON or failed
validation, `404` unknown book or route, `405` unsupported method, `413` body
over 1 MB.

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1
```
