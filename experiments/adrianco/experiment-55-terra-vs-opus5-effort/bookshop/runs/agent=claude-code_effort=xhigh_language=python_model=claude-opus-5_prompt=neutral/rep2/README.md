# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
Python standard library's **sqlite3** module. No ORM, no code generation — the
whole service is a few hundred lines.

## Requirements

- Python 3.9 or newer (verified on 3.11 and 3.14)
- Flask 2.3+ (the only runtime dependency; verified against Flask 2.3 and 3.0)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python wsgi.py
```

The server listens on <http://127.0.0.1:5000>. `flask --app wsgi run` works too,
as does any WSGI server pointed at `wsgi:app`, e.g.
`gunicorn 'wsgi:app'`.

Configuration is by environment variable:

| Variable                   | Default    | Meaning                                     |
| -------------------------- | ---------- | ------------------------------------------- |
| `BOOKAPI_DATABASE`         | `books.db` | SQLite file path (`:memory:` also works)    |
| `BOOKAPI_DATABASE_TIMEOUT` | `10`       | Seconds to wait for a write lock            |
| `HOST` / `PORT`            | `127.0.0.1` / `5000` | Bind address for `python wsgi.py` |

The schema is created automatically at startup if the file is new, so there is
no migration step.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

77 tests covering the full CRUD lifecycle, the author filter, validation,
persistence to disk, and JSON error handling. Each test runs against a fresh
SQLite file in a pytest `tmp_path`, so the suite never touches `books.db`.

## The book resource

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

- `id` — integer, assigned by the server.
- `title`, `author` — **required**, non-blank strings up to 500 characters.
  Surrounding whitespace is trimmed.
- `year` — optional integer between 1 and next year (a numeric string such as
  `"1925"` is accepted and stored as a number). `null` clears it.
- `isbn` — optional. Must be 10 or 13 digits once hyphens and spaces are
  removed (a trailing `X` is allowed on ISBN-10). Stored exactly as sent, so
  your formatting is preserved. `""` is treated as `null`.

Unknown fields in a request body are ignored.

## Endpoints

| Method   | Path           | Purpose                       | Success        |
| -------- | -------------- | ----------------------------- | -------------- |
| `GET`    | `/health`      | Liveness + database check     | `200`          |
| `POST`   | `/books`       | Create a book                 | `201` + `Location` |
| `GET`    | `/books`       | List books (`?author=` filter) | `200`         |
| `GET`    | `/books/{id}`  | Fetch one book                | `200`          |
| `PUT`    | `/books/{id}`  | Replace a book                | `200`          |
| `PATCH`  | `/books/{id}`  | Update selected fields        | `200`          |
| `DELETE` | `/books/{id}`  | Delete a book                 | `204`          |

Notes:

- `GET /books` returns a JSON **array** (`[]` when empty), ordered by `id`.
- `?author=` matches the whole author name, case-insensitively
  (`?author=jane austen` finds `Jane Austen`). An empty value is ignored.
- `PUT` is a full replacement: `title` and `author` are required, and any
  optional field you leave out is set to `null`. Use `PATCH` to change one
  field and leave the rest alone.
- `DELETE` returns `204` with an empty body; deleting an already-deleted book
  gives `404`.

### Status codes

| Code | When                                                             |
| ---- | ---------------------------------------------------------------- |
| 200  | Successful `GET`, `PUT`, `PATCH`                                  |
| 201  | Book created                                                     |
| 204  | Book deleted                                                     |
| 400  | Validation failed, or the body is not a JSON object              |
| 404  | No book with that id, or unknown route                           |
| 405  | Method not supported on that path                                |
| 500  | Unexpected server error                                          |
| 503  | `/health` could not reach the database                           |

Every response is JSON, including errors — the stock Flask HTML error pages are
replaced. Errors look like:

```json
{ "error": "Book 99 not found" }
```

Validation failures list every problem at once, so one round trip is enough to
fix the request:

```json
{
  "error": "Validation failed",
  "details": {
    "title": "title is required",
    "year": "year must be an integer"
  }
}
```

## Examples

```bash
# Health check
curl localhost:5000/health
# {"status":"ok","database":"ok"}

# Create
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"9780743273565"}'
# 201 {"id":1,"title":"The Great Gatsby",...}   Location: /books/1

# List, and list by author
curl localhost:5000/books
curl 'localhost:5000/books?author=F.%20Scott%20Fitzgerald'

# Fetch one
curl localhost:5000/books/1

# Replace
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Tender Is the Night","author":"F. Scott Fitzgerald","year":1934}'

# Update just the year
curl -X PATCH localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1934}'

# Delete
curl -i -X DELETE localhost:5000/books/1
# 204 No Content
```

## Layout

```
bookapi/
  __init__.py     create_app() — configuration and wiring
  routes.py       HTTP layer: one function per endpoint
  validation.py   payload validation and normalisation
  store.py        SQL for the books table, returns plain dicts
  db.py           connection lifecycle (one per request) and schema
  errors.py       JSON error responses for every failure mode
wsgi.py           entry point: python wsgi.py / flask --app wsgi run
tests/            pytest suite
```

Each request gets its own SQLite connection, stored on Flask's `g` and closed by
a teardown hook, which keeps the app safe under a threaded WSGI server. The
database runs in WAL mode so reads are not blocked by a concurrent write.
