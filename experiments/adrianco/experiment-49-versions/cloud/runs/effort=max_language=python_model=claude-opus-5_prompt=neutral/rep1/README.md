# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
Python standard library's **`sqlite3`** module. No ORM, no code generation —
just an application factory, a thin data-access layer and explicit validation.

## Requirements

- Python 3.8+
- Flask 2.3 or newer (the only runtime dependency)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the service

```bash
python run.py
```

The API listens on <http://127.0.0.1:5000> and creates `books.db` in the
working directory on first start. Alternatives:

```bash
flask --app run run --port 8000                 # Flask CLI
gunicorn --bind 0.0.0.0:5000 run:app            # any WSGI server
```

### Configuration

| Variable        | Default     | Purpose                                    |
| --------------- | ----------- | ------------------------------------------ |
| `BOOKS_DB_PATH` | `books.db`  | Path to the SQLite file                    |
| `HOST`          | `127.0.0.1` | Interface to bind (`python run.py` only)   |
| `PORT`          | `5000`      | Port to bind (`python run.py` only)        |
| `FLASK_DEBUG`   | unset       | `1` enables the debugger and auto-reloader |

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

84 tests cover the CRUD lifecycle, the author filter, pagination, validation,
error formatting and persistence across restarts. Each test runs against a
fresh SQLite file in a temporary directory, so the suite never touches a real
database and tests cannot leak state into one another.

## API

All responses are JSON. Times are ISO-8601 UTC strings.

| Method   | Path          | Success  | Description                            |
| -------- | ------------- | -------- | -------------------------------------- |
| `GET`    | `/health`     | 200      | Health check (also pings the database) |
| `POST`   | `/books`      | 201      | Create a book                          |
| `GET`    | `/books`      | 200      | List books, optionally filtered        |
| `GET`    | `/books/{id}` | 200      | Fetch one book                         |
| `PUT`    | `/books/{id}` | 200      | Update a book                          |
| `PATCH`  | `/books/{id}` | 200      | Update a book (alias of `PUT`)         |
| `DELETE` | `/books/{id}` | 204      | Delete a book                          |

### Book representation

```json
{
  "id": 1,
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0-452-28423-4",
  "created_at": "2026-07-25T21:45:15.482Z",
  "updated_at": "2026-07-25T21:45:15.482Z"
}
```

### `GET /health`

```bash
curl localhost:5000/health
# 200 {"status": "ok", "database": "connected"}
```

Returns `503` with `{"status": "error", ...}` if SQLite cannot be reached, so
it is usable as a container readiness probe.

### `POST /books`

`title` and `author` are required; `year` and `isbn` are optional.

```bash
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0-452-28423-4"}'
```

Responds `201` with the stored book and a `Location` header pointing at it.

### `GET /books`

Returns a JSON **array** (empty when there are no matches) plus an
`X-Total-Count` header carrying the total number of matching rows.

| Parameter | Description                                                |
| --------- | ---------------------------------------------------------- |
| `author`  | Exact, case-insensitive match on the author name            |
| `limit`   | Optional page size, `0`–`1000`                              |
| `offset`  | Optional number of rows to skip                             |

```bash
curl 'localhost:5000/books?author=george%20orwell'
curl 'localhost:5000/books?limit=20&offset=40'
```

Results are ordered by `id` ascending, i.e. insertion order.

### `GET /books/{id}`

```bash
curl localhost:5000/books/1     # 200, or 404 if no such book
```

### `PUT` / `PATCH` `/books/{id}`

Accepts either a complete representation or only the fields to change, so
`PUT` and `PATCH` behave identically:

```bash
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four"}'
```

Sending `null` for `year` or `isbn` clears the field. A body with none of the
four known fields is rejected with `400`. Unknown fields — including `id` and
the timestamps — are ignored.

### `DELETE /books/{id}`

```bash
curl -X DELETE localhost:5000/books/1     # 204 with an empty body
```

Deleting the same book twice returns `404` the second time.

## Validation rules

| Field    | Rule                                                                       |
| -------- | -------------------------------------------------------------------------- |
| `title`  | Required, non-blank string, ≤ 500 characters, stored trimmed                |
| `author` | Required, non-blank string, ≤ 255 characters, stored trimmed                |
| `year`   | Optional integer between 1 and 9999 (numeric strings such as `"1949"` are accepted) |
| `isbn`   | Optional 10- or 13-digit ISBN; hyphens and spaces allowed, stored verbatim  |

Blank strings for `year`/`isbn` are treated as "not supplied" and stored as
`null`. Validators report **every** problem in a payload rather than stopping
at the first one.

## Status codes and error format

| Code  | When                                                     |
| ----- | -------------------------------------------------------- |
| `200` | Successful `GET`, `PUT`, `PATCH`                          |
| `201` | Book created                                              |
| `204` | Book deleted                                              |
| `400` | Validation failure, malformed JSON, bad query parameter   |
| `404` | Unknown book or unknown route                             |
| `405` | Method not allowed for that path                          |
| `500` | Unexpected server error                                   |
| `503` | Database unreachable (`/health` only)                     |

Every error — including 404s and 405s that Flask would normally render as
HTML — comes back as JSON:

```json
{
  "error": "'title' is required; 'author' is required",
  "details": [
    {"message": "'title' is required", "field": "title"},
    {"message": "'author' is required", "field": "author"}
  ]
}
```

`error` is always a human-readable summary; `details` is present only for
validation failures and lists one entry per offending field.

## Project layout

```
.
├── bookapi/
│   ├── __init__.py      # create_app() application factory
│   ├── db.py            # connection lifecycle + schema bootstrap
│   ├── errors.py        # JSON error handlers
│   ├── repository.py    # all SQL lives here
│   ├── routes.py        # HTTP endpoints
│   └── validation.py    # payload validation (no Flask imports)
├── tests/
│   ├── conftest.py                  # fixtures: throwaway DB per test
│   ├── sample_data.py
│   ├── test_books_crud.py           # create / read / update / delete
│   ├── test_listing.py              # author filter + pagination
│   ├── test_validation.py           # validation over HTTP
│   ├── test_validation_unit.py      # validation as plain functions
│   ├── test_errors_and_persistence.py
│   └── test_health.py
├── run.py               # entry point / WSGI callable
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

## Design notes

- **Application factory.** `create_app()` takes a config mapping, which is what
  lets every test bind to its own database file.
- **Layering.** `validation.py` and `repository.py` have no Flask dependency;
  `routes.py` is the only module that touches HTTP. Validation logic is
  therefore testable as ordinary functions (`test_validation_unit.py`).
- **Connection handling.** One SQLite connection per request, stored on Flask's
  `g` and closed on teardown. Writes run inside `with conn:` so they commit or
  roll back atomically. WAL journaling is enabled to keep readers from blocking
  on writers.
- **Defence in depth.** The table carries `NOT NULL` and `CHECK` constraints
  mirroring the application-level rules, and the update path interpolates
  column names only from a fixed allow-list.
- **Forgiving input, strict storage.** A missing or wrong `Content-Type` header
  is tolerated and unknown fields are ignored, but anything actually stored has
  been validated and normalised.
