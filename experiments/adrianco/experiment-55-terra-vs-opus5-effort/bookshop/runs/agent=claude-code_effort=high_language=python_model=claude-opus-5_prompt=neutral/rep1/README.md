# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
Python standard library's **`sqlite3`** module.

## Why Flask

The task did not pin a framework. The pre-installed FastAPI (0.104.1) depends on
Pydantic 1.10.13, which fails to import on this environment's Python 3.14, so
Flask + `sqlite3` was chosen: both are already present and work on 3.14, and it
keeps the dependency surface to a single package.

## Requirements

- Python 3.10+
- Flask 2.3+ (`pytest` for the test suite)

## Setup

```bash
# optional but recommended
python3 -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
python3 app.py                 # http://127.0.0.1:8000
```

Or through the Flask CLI:

```bash
flask --app app run --port 8000
```

Configuration is read from the environment:

| Variable         | Default     | Purpose                             |
| ---------------- | ----------- | ----------------------------------- |
| `BOOKS_DB_PATH`  | `books.db`  | SQLite database file                |
| `HOST`           | `127.0.0.1` | Bind address                        |
| `PORT`           | `8000`      | Bind port                           |
| `FLASK_DEBUG`    | unset       | `1`/`true` enables the debug reloader |

The schema is created automatically on startup, so there is no migration step.

## Test

```bash
pytest
```

87 tests covering every endpoint, the validation rules, and the storage layer.

## API

All responses are JSON, except `204 No Content` on delete.

### `GET /health`

Liveness probe. Also runs a query against the `books` table, so it reports a
degraded database rather than only that the process is up.

```json
{ "status": "ok", "database": "ok" }
```

Returns `503` with `{"status": "error", ...}` if the database is unreachable.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are optional.

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

`201 Created`, with a `Location` header pointing at the new resource:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "created_at": "2026-07-30T00:57:19Z",
  "updated_at": "2026-07-30T00:57:19Z"
}
```

### `GET /books`

Returns a JSON array of all books, ordered by `id`.

| Query param | Behaviour                                          |
| ----------- | -------------------------------------------------- |
| `author`    | case-insensitive **substring** match on the author |
| `year`      | exact publication year                             |

```bash
curl 'http://127.0.0.1:8000/books?author=tolkien'
curl 'http://127.0.0.1:8000/books?author=tolkien&year=1937'
```

Both filters may be combined. A blank value (`?author=`) is ignored rather than
matching nothing. Wildcard characters in the filter are escaped, so `?author=%`
matches a literal `%`, not everything.

### `GET /books/{id}`

Returns a single book, or `404` if the id does not exist.

### `PUT /books/{id}`

**Full update.** `title` and `author` are required, and any optional field you
omit is cleared to `null` — the body is the complete new representation.

```bash
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

### `PATCH /books/{id}`

**Partial update** (an addition beyond the required endpoints, provided because
full-replace `PUT` is awkward for one-field edits). Only the supplied fields
change; sending `{"year": null}` clears just that field. An empty body is a
`400`.

```bash
curl -X PATCH http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1969}'
```

### `DELETE /books/{id}`

`204 No Content` on success, `404` if the book does not exist.

## Validation rules

| Field    | Rule                                                                       |
| -------- | -------------------------------------------------------------------------- |
| `title`  | **required**, non-empty string after trimming, ≤ 500 characters            |
| `author` | **required**, non-empty string after trimming, ≤ 255 characters            |
| `year`   | optional integer (numeric strings accepted), `1` … next calendar year      |
| `isbn`   | optional string ≤ 20 chars of digits, `X`, hyphens and spaces; **unique**  |

Notes on the deliberate choices here:

- Leading/trailing whitespace is trimmed; a value of `"   "` counts as empty.
- `true`/`false` are rejected for `year` (Python would otherwise coerce `True`
  to `1`).
- `year` allows next year because pre-release titles carry a future date.
- `isbn` is checked for **shape only** — no check-digit validation — so test and
  catalogue data are not rejected. It is stored as given, and a unique partial
  index enforces uniqueness while still allowing many books with no ISBN.
- Unknown fields in the body (e.g. `id`, `created_at`) are ignored, so clients
  can safely round-trip a response object back to the server.
- A JSON body is accepted even when `Content-Type` is missing, since
  `curl -d '{...}'` omits it by default.

## Status codes

| Code  | When                                                       |
| ----- | ---------------------------------------------------------- |
| `200` | Successful `GET`, `PUT`, `PATCH`                            |
| `201` | Book created                                                |
| `204` | Book deleted                                                |
| `400` | Validation failure, malformed/non-JSON body, bad filter     |
| `404` | Unknown book id or unknown route                            |
| `405` | Method not allowed on a valid route                         |
| `409` | `isbn` already belongs to another book                      |
| `503` | Health check could not reach the database                   |

Validation failures name every offending field at once rather than stopping at
the first:

```json
{
  "error": "Validation failed",
  "details": {
    "title": "'title' is required",
    "year": "'year' must be an integer"
  }
}
```

## Project layout

```
app.py                    # entry point — creates the app, runs the dev server
bookapi/
  __init__.py             # application factory + JSON error handlers
  db.py                   # schema, per-request SQLite connection
  routes.py               # HTTP endpoints
  validation.py           # payload validation (no framework dependency)
tests/
  conftest.py             # app/client fixtures on a temp database
  test_books_api.py       # endpoint behaviour, filters, status codes
  test_validation.py      # validation unit tests
  test_persistence.py     # storage, restart durability, injection safety
```

Every SQL statement uses bound parameters; `LIKE` filters additionally escape
wildcards.

## Notes and limitations

- The database connection is opened per request and closed on teardown, which
  respects SQLite's one-connection-per-thread rule. WAL journalling is enabled
  so reads do not block on a concurrent write.
- `flask run` / `python app.py` starts Werkzeug's development server. For
  production use a WSGI server, e.g.
  `gunicorn 'app:app'` — though SQLite limits you to a single writer.
- There is no authentication, pagination, or rate limiting; none was requested.
