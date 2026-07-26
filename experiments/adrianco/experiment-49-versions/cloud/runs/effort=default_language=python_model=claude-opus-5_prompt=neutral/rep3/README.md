# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
Python standard-library **`sqlite3`** module. No ORM, no code generation — the
whole service is three files.

| File            | Purpose                                              |
| --------------- | ---------------------------------------------------- |
| `app.py`        | Flask application factory, routes, error handling     |
| `db.py`         | SQLite schema, per-request connection, row → JSON     |
| `validation.py` | Payload validation rules                              |
| `test_api.py`   | Integration tests (33 of them) driving the real app   |

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

## Run

```bash
python3 app.py                 # http://127.0.0.1:8000
```

Or via the Flask CLI (it auto-discovers the `create_app` factory):

```bash
flask --app app run --port 8000
```

Configuration comes from two environment variables:

| Variable        | Default   | Meaning                        |
| --------------- | --------- | ------------------------------ |
| `BOOKS_DB_PATH` | `books.db` | SQLite file (created on start) |
| `PORT`          | `8000`    | Port for `python3 app.py`      |

The schema is created automatically on startup, so there is no migration step.

## Test

```bash
python3 -m pytest -q
```

Every test gets its own temporary SQLite file (via pytest's `tmp_path`), so the
suite is isolated from your development database and from itself.

## API

All responses are JSON, except `204 No Content` on delete.

### `GET /health`

```bash
curl http://127.0.0.1:8000/health
# 200 {"status": "ok", "database": "ok"}
```

Returns `503` with `{"status": "error", ...}` if the database is unreachable.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are optional.

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "created_at": "2026-07-25T18:30:00Z",
  "updated_at": "2026-07-25T18:30:00Z"
}
```

`201 Created` with a `Location: /books/1` header.

### `GET /books`

Returns a JSON array ordered by id, oldest first.

```bash
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=frank%20herbert'
```

The `?author=` filter is an exact, **case-insensitive** match. A blank value
(`?author=`) is treated as no filter. No match returns `200` with `[]`, not a 404.

### `GET /books/{id}`

`200` with the book, or `404` if there is no such id.

### `PUT /books/{id}`

Replaces the book — this is a full update, not a patch. Any field you omit is
reset, so `{"title": "...", "author": "..."}` clears `year` and `isbn`.
Returns `200` with the updated book, or `404` if the id does not exist.

```bash
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
```

### `DELETE /books/{id}`

`204 No Content` with an empty body, or `404` if the id does not exist.

## Validation

| Field    | Rule                                                                       |
| -------- | -------------------------------------------------------------------------- |
| `title`  | **required** — non-empty string after trimming, ≤ 500 chars                 |
| `author` | **required** — non-empty string after trimming, ≤ 500 chars                 |
| `year`   | optional integer between 1000 and next calendar year                        |
| `isbn`   | optional — hyphens/spaces stripped, then must be 10 or 13 characters, unique |

Unknown fields are rejected rather than silently ignored, so a typo like
`"athor"` surfaces as a `400` instead of quietly dropping data.

## Status codes

| Code  | When                                                                   |
| ----- | ---------------------------------------------------------------------- |
| `200` | Successful `GET` / `PUT`                                               |
| `201` | Book created                                                           |
| `204` | Book deleted                                                           |
| `400` | Validation failed, malformed JSON, or a non-JSON `Content-Type`         |
| `404` | No book with that id, or an unknown route                              |
| `405` | Method not allowed on a known route                                    |
| `409` | The supplied `isbn` already belongs to another book                    |
| `500` | Unexpected server error                                                |
| `503` | Health check could not reach SQLite                                    |

Errors share one shape, with `details` present only for validation failures:

```json
{
  "error": "Validation failed",
  "details": {"title": "'title' is required"}
}
```

Werkzeug's default HTML error pages are overridden, so even a `404` on an
unknown route comes back as JSON.

## Design notes

- **Application factory.** `create_app(database=...)` means tests point at a
  temp file instead of monkey-patching a module-level global. Importing `app.py`
  has no side effects.
- **Connection per request.** Opened lazily in `flask.g`, closed by
  `teardown_appcontext`. Avoids sharing a SQLite connection across threads.
- **Parameterised SQL everywhere.** No string interpolation into queries.
- **ISBN normalisation.** `978-0-441-01359-3` and `9780441013593` are stored as
  the same value, so the `UNIQUE` constraint catches duplicates that differ only
  in punctuation. Multiple books may have a `NULL` isbn — SQLite's `UNIQUE`
  does not constrain nulls.
- **Timestamps** are UTC ISO-8601, generated by SQLite so they don't depend on
  the application server's clock handling.

## Production

The built-in server is Flask's development server. For real deployment use a
WSGI server:

```bash
pip install gunicorn
gunicorn 'app:create_app()' --bind 0.0.0.0:8000
```

SQLite serialises writes, so keep the worker count modest or move to Postgres if
write concurrency matters.
