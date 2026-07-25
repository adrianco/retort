# Books API

A small REST service for managing a book collection, built with **Flask** and the
Python standard library's **`sqlite3`** module. No ORM, no code generation — the
whole thing is four modules and a schema.

## Requirements

- Python 3.9+
- Flask 2.3+ (the only runtime dependency; `sqlite3` ships with Python)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt # runtime + test deps
```

## Run

```bash
flask --app app run                # http://127.0.0.1:5000
python app.py                      # same thing, honours HOST/PORT
```

The `books` table is created automatically on startup if it does not exist, so
there is no migration step. To create the database file up front:

```bash
flask --app app init-db
```

### Configuration

| Variable         | Default     | Purpose                                   |
| ---------------- | ----------- | ----------------------------------------- |
| `BOOKS_DATABASE` | `books.db`  | Path to the SQLite file                    |
| `HOST`           | `127.0.0.1` | Bind address (`python app.py` only)        |
| `PORT`           | `5000`      | Bind port (`python app.py` only)           |
| `FLASK_DEBUG`    | unset       | `1`/`true` enables the reloader + debugger |

`create_app()` is a standard application factory, so any WSGI server works in
production, e.g. `gunicorn "app:create_app()"`.

## API

All responses are JSON (including errors). Request bodies must be JSON objects;
`Content-Type: application/json` is recommended but not required.

| Method   | Path              | Success        | Description                            |
| -------- | ----------------- | -------------- | -------------------------------------- |
| `GET`    | `/health`         | `200` / `503`  | Liveness + database round-trip         |
| `POST`   | `/books`          | `201`          | Create a book (sets `Location` header) |
| `GET`    | `/books`          | `200`          | List books, optional `?author=` filter |
| `GET`    | `/books/{id}`     | `200`          | Fetch one book                         |
| `PUT`    | `/books/{id}`     | `200`          | Replace a book                         |
| `DELETE` | `/books/{id}`     | `204`          | Delete a book (empty body)             |

### Book resource

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "created_at": "2026-07-24T18:43:26+00:00",
  "updated_at": "2026-07-24T18:43:26+00:00"
}
```

| Field    | Type           | Rules                                                        |
| -------- | -------------- | ------------------------------------------------------------ |
| `title`  | string         | **required**, non-blank, ≤ 500 chars, trimmed                 |
| `author` | string         | **required**, non-blank, ≤ 500 chars, trimmed                 |
| `year`   | integer / null | optional, 1000 – next calendar year; `true`/`"1965"` rejected |
| `isbn`   | string / null  | optional, ISBN-10 or ISBN-13, **unique** across the collection |

`id`, `created_at` and `updated_at` are server-managed and ignored (in fact
rejected — see below) if sent by a client.

Notes on behaviour:

- **`PUT` is a full replacement.** Fields omitted from the body are reset to
  `null`, so send the whole resource. There is no `PATCH`.
- **Unknown fields are rejected** with `400` rather than silently dropped, so a
  typo such as `{"tittle": "Dune"}` is reported instead of losing data.
- **ISBNs are normalised** — hyphens and spaces are stripped and a trailing `x`
  check digit is upper-cased, so `978-0-441-01359-3` and `9780441013593` are the
  same book. Format is validated, not the checksum.
- **`?author=` matches the full author name**, case-insensitively and ignoring
  surrounding whitespace. `?author=Ursula` does not match "Ursula K. Le Guin".
- **Listing is newest-first** (descending `id`).

### Errors

Failures share one shape; validation errors add a per-field `details` map:

```json
{
  "error": "Validation failed",
  "details": {
    "title": "'title' is required",
    "year": "'year' must be between 1000 and 2027"
  }
}
```

| Status | When                                                        |
| ------ | ----------------------------------------------------------- |
| `400`  | Body is not valid JSON, or a field fails validation          |
| `404`  | No book with that id, or unknown route                       |
| `405`  | Method not supported on that path                            |
| `409`  | Another book already has that ISBN                           |
| `503`  | `/health` could not reach the database                       |

### Examples

```bash
# Create
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

# List / filter
curl localhost:5000/books
curl -G localhost:5000/books --data-urlencode 'author=Frank Herbert'

# Read, replace, delete
curl localhost:5000/books/1
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
     -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:5000/books/1
```

## Tests

```bash
python -m pytest -q          # 87 tests, ~0.2s
```

`test_api.py` drives every endpoint over HTTP through Flask's test client
against a real SQLite file (one temporary database per test, so tests are
isolated and can run in any order); it covers the happy paths, validation
failures, 404/405/409 handling, and persistence across an application restart.
`test_validation.py` unit-tests the validation rules directly.

## Layout

| File                 | Responsibility                                            |
| -------------------- | --------------------------------------------------------- |
| `app.py`             | Application factory, routes, JSON error handlers           |
| `repository.py`      | SQL for the `books` table; framework-agnostic              |
| `validation.py`      | Payload validation; no Flask or SQLite imports             |
| `db.py`              | Connection lifecycle (per request) and schema creation     |
| `conftest.py`        | pytest fixtures (temp database, client, seeded book)       |
| `test_api.py`        | Integration tests over HTTP                                |
| `test_validation.py` | Unit tests for the validation rules                        |

One SQLite connection is opened per request and closed on teardown, so the
threaded dev server and multi-worker WSGI servers are both safe.
