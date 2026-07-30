# Book Collection API

A small JSON REST API for managing a collection of books, built with **Flask** and
the Python standard library's **sqlite3** module (no ORM, no other runtime
dependencies).

## Requirements

- Python 3.9+ (developed and tested on 3.14)
- Flask 2.3+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on <http://127.0.0.1:5000> and creates `books.db` in the
working directory on first start. Configuration comes from the environment:

| Variable         | Default     | Meaning                              |
| ---------------- | ----------- | ------------------------------------ |
| `BOOKS_DATABASE` | `books.db`  | Path to the SQLite file              |
| `HOST`           | `127.0.0.1` | Interface to bind                    |
| `PORT`           | `5000`      | Port to bind                         |
| `FLASK_DEBUG`    | unset       | Set to `1` for the reloader/debugger |

`app.py` exposes a `create_app(database_path=None)` factory, so any WSGI server
can serve it:

```bash
pip install gunicorn
gunicorn --bind 127.0.0.1:5000 "app:create_app()"
```

## Tests

```bash
python -m pytest
```

82 tests run against a temporary SQLite file per test, so they leave no state
behind and need no running server:

- `tests/test_api.py` — integration tests through Flask's test client: the full
  CRUD lifecycle, the `?author=` filter, status codes, error bodies, ISBN
  uniqueness, and persistence across app restarts.
- `tests/test_validation.py` — unit tests for the validation rules.

## API

All responses are JSON, except `204 No Content` on a successful delete.

### `GET /health`

```bash
curl http://127.0.0.1:5000/health
```

```json
{ "status": "ok", "database": "ok" }
```

Returns `503` with `{"status": "unhealthy", ...}` if the database cannot be
reached.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are
optional. Responds `201` with the created book and a `Location` header.

```bash
curl -X POST http://127.0.0.1:5000/books \
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
  "created_at": "2026-07-30T03:47:01Z",
  "updated_at": "2026-07-30T03:47:01Z"
}
```

### `GET /books`

Lists books ordered by `id`, as a JSON array. Pass `?author=` to filter by
author; the match is exact but case-insensitive, and a blank value is ignored.

```bash
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'
```

### `GET /books/{id}`

Returns one book, or `404` if the id is unknown.

### `PUT /books/{id}`

Replaces the book. As with any PUT, the body is the new representation of the
resource: `title` and `author` are required, and **omitted optional fields are
cleared** (set to `null`). Responds `200` with the updated book.

```bash
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

### `PATCH /books/{id}`

Not required by the spec, but provided because partial updates are what callers
usually want. Only the supplied fields change; at least one must be present.

```bash
curl -X PATCH http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'
```

### `DELETE /books/{id}`

Deletes the book and responds `204` with an empty body, or `404` if the id is
unknown.

## Validation rules

| Field    | Rule                                                                        |
| -------- | --------------------------------------------------------------------------- |
| `title`  | Required. Non-blank string, ≤ 500 characters. Surrounding whitespace trimmed |
| `author` | Required. Same rules as `title`                                             |
| `year`   | Optional. Integer (or an integer-valued string) between 1 and 2200           |
| `isbn`   | Optional. ISBN-10 or ISBN-13; hyphens/spaces are stripped before storing     |

Unknown fields are rejected rather than ignored, so a typo such as `athor`
fails loudly. ISBNs are checked for shape (10 or 13 characters, with an
optional trailing `X` on an ISBN-10) but the check digit is not verified.
An ISBN, when given, must be unique across the collection.

## Status codes

| Code  | When                                                              |
| ----- | ----------------------------------------------------------------- |
| `200` | Successful `GET`, `PUT`, `PATCH`                                   |
| `201` | Book created                                                      |
| `204` | Book deleted                                                      |
| `400` | Validation failure, or a body that is not a JSON object            |
| `404` | Unknown book id or unknown route                                  |
| `405` | Method not allowed for that path                                  |
| `409` | The ISBN is already used by another book                          |
| `415` | `Content-Type` was not `application/json` on a write              |
| `500` | Unexpected server/database error                                  |
| `503` | Health check failed to reach the database                         |

Errors carry a message, and validation errors additionally report every
offending field at once:

```json
{
  "error": "validation failed",
  "details": { "title": "is required", "year": "must be an integer" }
}
```

## Layout

| File                      | Purpose                                                     |
| ------------------------- | ----------------------------------------------------------- |
| `app.py`                  | App factory, routes, JSON error handlers, dev entry point    |
| `database.py`             | Schema and SQLite access (one connection per app context)    |
| `validation.py`           | Payload validation, independent of Flask and of the database |
| `tests/`                  | pytest suite                                                 |

## Design notes

- **Storage.** `books` has an autoincrementing `id`, `NOT NULL` title/author,
  nullable `year`/`isbn`, and `created_at`/`updated_at` timestamps in UTC.
  `isbn` carries a `UNIQUE` constraint — SQLite permits many `NULL`s in a
  unique column, so untracked books coexist happily, while a duplicate ISBN is
  surfaced as `409` rather than a `500`.
- **Connections.** One `sqlite3` connection per Flask application context,
  closed on teardown, so requests never share a connection across threads. WAL
  journalling is enabled for better read/write concurrency.
- **All queries are parameterised**, so user input can never be interpolated
  into SQL. The `?author=` filter uses `COLLATE NOCASE` (ASCII case folding).
- **Errors are always JSON**, including Flask's built-in 404/405 responses,
  which would otherwise be HTML.
