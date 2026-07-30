# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (Python's standard-library `sqlite3` — no ORM, no other runtime
dependencies).

## Requirements

- Python 3.9+
- Flask 2.3 or newer (`pip install -r requirements.txt`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # app + pytest
```

## Run

```bash
python wsgi.py                     # http://127.0.0.1:5000
```

Equivalent alternatives:

```bash
flask --app wsgi run               # Flask CLI
flask --app wsgi run --debug       # auto-reload
gunicorn 'wsgi:app'                # if gunicorn is installed
```

The schema is created automatically on startup, so there is no migration step.
Configuration comes from the environment:

| Variable            | Default     | Purpose                             |
| ------------------- | ----------- | ----------------------------------- |
| `BOOK_API_DATABASE` | `books.db`  | Path to the SQLite database file     |
| `HOST`              | `127.0.0.1` | Bind address (`python wsgi.py`)      |
| `PORT`              | `5000`      | Bind port (`python wsgi.py`)         |
| `FLASK_DEBUG`       | unset       | `1`/`true` enables the debugger      |

To create the database up front (optional): `flask --app wsgi init-db`.

## Test

```bash
pytest                             # 83 tests
```

`pytest` is configured in `pyproject.toml` (`testpaths`, `pythonpath`), so it
works from the project root with no extra flags. Every test builds its own app
against a throwaway SQLite file in `tmp_path`, so runs are isolated and leave
nothing behind.

## Endpoints

| Method   | Path          | Success        | Notes                                     |
| -------- | ------------- | -------------- | ----------------------------------------- |
| `GET`    | `/health`     | `200` / `503`  | `503` if the database does not answer      |
| `GET`    | `/`           | `200`          | Endpoint listing                           |
| `POST`   | `/books`      | `201`          | Sets a `Location` header                   |
| `GET`    | `/books`      | `200`          | `?author=`, `?limit=`, `?offset=`          |
| `GET`    | `/books/{id}` | `200`          | `404` if unknown                           |
| `PUT`    | `/books/{id}` | `200`          | Full replacement                           |
| `PATCH`  | `/books/{id}` | `200`          | Partial update                             |
| `DELETE` | `/books/{id}` | `204`          | `404` if unknown                           |

### Book representation

```json
{
  "id": 1,
  "title": "Nineteen Eighty-Four",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "9780451524935",
  "created_at": "2026-07-29T18:08:32.606794Z",
  "updated_at": "2026-07-29T18:08:32.606794Z"
}
```

`GET /books` returns a bare JSON array of these objects, plus an
`X-Total-Count` header carrying the number of matching books (which differs
from the page size when `?limit=` is used).

### Examples

```bash
# Create
curl -i -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0-451-52493-5"}'

# List, and list by author (case-insensitive)
curl localhost:5000/books
curl 'localhost:5000/books?author=george%20orwell'

# Read one
curl localhost:5000/books/1

# Replace (title and author required; year/isbn omitted here are cleared)
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949}'

# Update just one field
curl -X PATCH localhost:5000/books/1 -H 'Content-Type: application/json' -d '{"year":1950}'

# Delete
curl -i -X DELETE localhost:5000/books/1

# Health
curl localhost:5000/health
```

## Validation

| Field    | Rule                                                                              |
| -------- | --------------------------------------------------------------------------------- |
| `title`  | **Required.** Non-blank string, trimmed, ≤ 500 characters.                         |
| `author` | **Required.** Non-blank string, trimmed, ≤ 200 characters.                         |
| `year`   | Optional. Integer between 1 and next year (upcoming releases are allowed), or null. |
| `isbn`   | Optional. 10 digits (last may be `X`) or 13 digits, after spaces/hyphens are stripped. Must be unique. |

Behaviour worth knowing:

- All field problems in a request are reported together, not one at a time.
- Unknown fields (including `id`) are ignored rather than rejected, so clients
  can round-trip a full book object back to `PUT`.
- `PUT` is a full replacement per REST semantics: `title` and `author` are
  required and omitted optional fields become `null`. Use `PATCH` to change a
  subset of fields.
- `isbn` is normalised before storage, so `978-0-451-52493-5` and
  `9780451524935` are the same book. The check digit itself is not verified.
- An empty-string `isbn` means "no ISBN" rather than a validation error.
- `Content-Type: application/json` is not enforced; any body that parses as
  JSON is accepted.

## Error responses

Every error — validation, missing rows, unknown routes, wrong methods,
unexpected crashes — is JSON:

```json
{
  "error": "validation_failed",
  "message": "The submitted book is not valid.",
  "details": { "title": "title is required.", "year": "year must be an integer or null." }
}
```

`details` is only present when there is something field-specific to report.

| Status | `error`                 | When                                            |
| ------ | ----------------------- | ----------------------------------------------- |
| `400`  | `validation_failed`     | Bad field values, non-object body, invalid JSON  |
| `404`  | `not_found`             | Unknown book id or unknown route                 |
| `405`  | `method_not_allowed`    | Wrong method for a known path                    |
| `409`  | `conflict`              | ISBN already used by another book                |
| `500`  | `internal_server_error` | Unexpected failure (logged server-side)          |
| `503`  | `unavailable` database  | `/health` when SQLite cannot be queried          |

## Layout

```
bookapi/
  __init__.py     app factory (create_app)
  routes.py       HTTP endpoints
  validation.py   payload validation, all errors collected per request
  repository.py   SQL against the books table
  db.py           connection lifecycle (one per request), schema, init-db CLI
  errors.py       ApiError types and the JSON error handlers
wsgi.py           entry point
tests/            pytest suite (health, CRUD, validation, errors, persistence)
```

The layers only depend downwards: `routes` knows no SQL, `repository` knows no
Flask, and `validation` knows neither.

### Storage notes

`books` has an `AUTOINCREMENT` primary key (ids are never reused), a `UNIQUE`
`isbn`, and a `NOCASE` index on `author` backing the `?author=` filter. One
connection is opened per request and closed on teardown, so threads never share
one; writes go through `with conn:` transactions and WAL journalling is enabled
for file-backed databases.
