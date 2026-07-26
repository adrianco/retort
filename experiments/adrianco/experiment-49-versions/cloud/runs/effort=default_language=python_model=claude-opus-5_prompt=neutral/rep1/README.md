# Book Collection API

A small REST service for managing a book collection, built with **Flask** and the
standard library's **sqlite3** module. No ORM, no code generation — the whole
service is ~300 lines across three modules.

## Requirements

- Python 3.10+
- Flask 2.3+ (`pytest` for the test suite)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python wsgi.py                    # http://127.0.0.1:5000
```

Or via the Flask CLI (with reloader/debugger):

```bash
flask --app wsgi run --debug
```

The SQLite schema is created automatically on startup. The database file
defaults to `books.sqlite3` in the project root; override it with the
`BOOKS_DATABASE` environment variable. `HOST` and `PORT` are also honoured by
`python wsgi.py`.

```bash
BOOKS_DATABASE=/var/lib/books.sqlite3 PORT=8080 python wsgi.py
```

For a production deployment, serve the WSGI app with a real server:

```bash
pip install gunicorn && gunicorn wsgi:app
```

## Test

```bash
python -m pytest            # 52 tests
python -m pytest -v         # per-test names
```

Each test gets a fresh SQLite file in pytest's `tmp_path`, so runs are isolated
and leave nothing behind.

## API

| Method   | Path           | Purpose                              | Success |
| -------- | -------------- | ------------------------------------ | ------- |
| `GET`    | `/health`      | Liveness + database connectivity     | 200     |
| `POST`   | `/books`       | Create a book                        | 201     |
| `GET`    | `/books`       | List books (`?author=` filter)       | 200     |
| `GET`    | `/books/{id}`  | Fetch one book                       | 200     |
| `PUT`    | `/books/{id}`  | Replace a book                       | 200     |
| `DELETE` | `/books/{id}`  | Delete a book                        | 204     |

### Book representation

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

### Fields and validation

| Field    | Required | Rules                                                         |
| -------- | -------- | ------------------------------------------------------------- |
| `title`  | yes      | Non-empty string, ≤ 500 chars, trimmed                        |
| `author` | yes      | Non-empty string, ≤ 500 chars, trimmed                        |
| `year`   | no       | Integer 1–9999, or `null`                                     |
| `isbn`   | no       | Valid ISBN-10 or ISBN-13 (checksum verified), unique, or `null` |

Notes:

- ISBNs are normalized before storage — `978-0-441-01359-3` and
  `978 0 441 01359 3` are both stored as `9780441013593`.
- Unknown fields in the body are rejected rather than silently ignored, so
  typos like `"tilte"` surface as a 400 instead of a missing title.
- All validation problems in a request are reported together, not one at a time.

### Status codes

| Code | When                                                            |
| ---- | --------------------------------------------------------------- |
| 400  | Malformed JSON, wrong `Content-Type`, or failed field validation |
| 404  | No book with that ID (or unknown route)                          |
| 405  | Method not allowed on the path                                   |
| 409  | The ISBN already belongs to another book                         |
| 503  | Health check could not reach the database                        |

Errors are always JSON:

```json
{
  "error": "Validation failed",
  "details": { "title": "is required", "year": "must be an integer" }
}
```

## Examples

```bash
# Create — returns 201 with a Location header
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

# List everything
curl localhost:5000/books

# Filter by author (case-insensitive exact match on the full name)
curl 'localhost:5000/books?author=frank+herbert'

# Fetch one
curl localhost:5000/books/1

# Replace — PUT is a full replacement, so omitted optional fields are cleared
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe Edition)","author":"Frank Herbert","year":1965}'

# Delete — 204 with an empty body
curl -X DELETE localhost:5000/books/1

# Health
curl localhost:5000/health
```

`GET /books` wraps the collection so it can grow without a breaking change:

```json
{ "books": [ ... ], "count": 2 }
```

## Layout

```
books/
  __init__.py     application factory, JSON error handlers
  api.py          routes
  db.py           connection lifecycle, schema, `flask init-db` command
  validation.py   payload validation (pure functions, no Flask dependency)
wsgi.py           entry point — exposes `app` for gunicorn/uvicorn
tests/
  conftest.py         app/client/make_book fixtures
  test_books_api.py   integration tests through the HTTP layer
  test_validation.py  unit tests for the validation rules
```

## Design notes

- **One connection per request**, stashed on `flask.g` and closed by
  `teardown_appcontext`, so a handler's reads and writes share a transaction.
- **Validation is separated from HTTP** — `validate_book` takes a dict and
  raises `ValidationError`; an error handler turns that into a 400. The rules
  are therefore unit-testable without spinning up a client.
- **Uniqueness is enforced by the database**, not a read-then-write check. The
  `UNIQUE` constraint on `isbn` makes duplicate detection race-free; the
  `IntegrityError` is translated into a 409.
- **`PUT` validates before checking existence**, so a malformed body aimed at a
  missing ID reports the body problem (400) rather than a misleading 404.
- The `author` index uses `COLLATE NOCASE` to match the filter's semantics.
