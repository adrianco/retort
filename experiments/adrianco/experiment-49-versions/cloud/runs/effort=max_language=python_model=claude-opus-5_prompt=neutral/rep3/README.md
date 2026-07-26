# Book Collection API

A small REST service for managing a book collection, built with **Flask** and the
standard library's **`sqlite3`** module. No ORM, no code generation — just a thin
HTTP layer over a well-defined schema.

- Full CRUD over `/books`, plus an `?author=` filter and a `GET /health` check
- Data persisted in an embedded SQLite database
- Every response — success *and* failure — is JSON, with appropriate status codes
- 101 tests covering the endpoints, validation, error rendering, and persistence

---

## Requirements

- Python 3.9+
- Flask 2.3 or newer (the only runtime dependency; `sqlite3` ships with Python)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements.txt` holds the runtime dependency alone; `requirements-dev.txt`
adds `pytest`. If Flask and pytest are already installed system-wide, you can
skip the virtualenv entirely.

## Running

```bash
python app.py
```

The service listens on <http://127.0.0.1:8000> and creates its database on first
start. It also works through the Flask CLI, which discovers the `create_app`
application factory:

```bash
flask --app bookapi run --port 8000
```

For production, point any WSGI server at the same factory:

```bash
gunicorn 'bookapi:create_app()'
```

## Running the tests

```bash
pytest
```

101 tests, no network or fixtures required — each one runs against a fresh
SQLite file in a pytest `tmp_path`.

## Configuration

All settings are optional and read from the environment at startup.

| Variable            | Default                | Purpose                                    |
| ------------------- | ---------------------- | ------------------------------------------ |
| `BOOKS_DB_PATH`     | `instance/books.db`    | Location of the SQLite database file       |
| `BOOKS_DB_TIMEOUT`  | `5.0`                  | Seconds to wait on a locked database       |
| `PORT`              | `8000`                 | Port for `python app.py`                   |
| `HOST`              | `127.0.0.1`            | Bind address for `python app.py`           |
| `FLASK_DEBUG`       | off                    | Set to `1` for the reloader and debugger   |

---

## API

Base URL: `http://127.0.0.1:8000`

### The book resource

| Field    | Type              | Required | Notes                                        |
| -------- | ----------------- | -------- | -------------------------------------------- |
| `id`     | integer           | —        | Server-assigned, read-only, never reused      |
| `title`  | string            | **yes**  | Trimmed; 1–512 characters                     |
| `author` | string            | **yes**  | Trimmed; 1–512 characters                     |
| `year`   | integer or `null` | no       | Between -3000 and 3000                        |
| `isbn`   | string or `null`  | no       | Up to 32 characters; unique across the shelf  |

### Endpoints

| Method   | Path           | Success | Description                              |
| -------- | -------------- | ------- | ---------------------------------------- |
| `GET`    | `/health`      | 200     | Liveness check, including a database ping |
| `POST`   | `/books`       | 201     | Create a book                             |
| `GET`    | `/books`       | 200     | List books; supports `?author=`           |
| `GET`    | `/books/{id}`  | 200     | Fetch one book                            |
| `PUT`    | `/books/{id}`  | 200     | Replace a book                            |
| `PATCH`  | `/books/{id}`  | 200     | Update selected fields of a book          |
| `DELETE` | `/books/{id}`  | 204     | Delete a book                             |

Status codes returned: `200`, `201`, `204`, `400` (validation), `404` (unknown
book or route), `405` (wrong method), `409` (duplicate ISBN), `413` (body over
256 KB), `500` (unexpected), `503` (database unreachable, from `/health`).

---

### `GET /health`

```bash
curl http://127.0.0.1:8000/health
```

```json
{ "status": "ok", "database": "ok" }
```

Runs an actual `SELECT` against SQLite rather than just returning a constant, so
a broken or unreachable database surfaces as `503` with
`{"status": "error", "database": "unavailable"}`.

### `POST /books`

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "9780451524935"}'
```

`201 Created`, with a `Location: /books/1` header:

```json
{
  "id": 1,
  "title": "Nineteen Eighty-Four",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "9780451524935"
}
```

`year` and `isbn` may be omitted or `null`; they default to `null`.

### `GET /books`

```bash
curl http://127.0.0.1:8000/books
curl 'http://127.0.0.1:8000/books?author=George%20Orwell'
```

Returns a JSON array ordered by `id`, i.e. by insertion:

```json
[
  { "id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "9780451524935" },
  { "id": 2, "title": "Animal Farm", "author": "George Orwell", "year": 1945, "isbn": null }
]
```

The `?author=` filter is an **exact, case-insensitive** match (`george orwell`
finds `George Orwell`). A blank value is treated as no filter. No match is an
empty array with `200`, not a `404` — the collection exists, it is just empty.

### `GET /books/{id}`

```bash
curl http://127.0.0.1:8000/books/1
```

`404` if no book has that id.

### `PUT /books/{id}`

Replaces the resource, so the body must describe the whole book: `title` and
`author` are required, and **any omitted optional field is cleared to `null`**.

```bash
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Animal Farm", "author": "George Orwell", "year": 1945}'
```

The `id` from a `GET` response may be left in the body; it is ignored, so a
fetched book can be edited and sent straight back.

### `PATCH /books/{id}`

For partial updates, where `PUT`'s clear-what-you-omit behaviour is not wanted.
Only the supplied fields change, and at least one must be given.

```bash
curl -X PATCH http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1950}'
```

### `DELETE /books/{id}`

```bash
curl -i -X DELETE http://127.0.0.1:8000/books/1
```

`204 No Content` with an empty body; `404` if the book is already gone.

---

## Errors

Every error, including ones raised by the routing layer, uses one shape:

```json
{
  "error": "validation_error",
  "message": "The request body failed validation.",
  "details": { "title": "'title' is required." }
}
```

- `error` — a stable slug to branch on in code
- `message` — a human-readable summary
- `details` — present only for field-level problems, keyed by field name

Validation reports **all** bad fields at once rather than failing on the first:

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' -d '{"title": "", "author": 7, "year": "soon"}'
```

```json
{
  "error": "validation_error",
  "message": "The request body failed validation.",
  "details": {
    "title": "'title' must not be empty.",
    "author": "'author' must be a string.",
    "year": "'year' must be an integer."
  }
}
```

---

## Design notes

**Layering.** `routes` handles HTTP, `validation` cleans input, `repository`
owns the SQL, `db` owns connections, `errors` owns rendering. Each layer is
independently testable, and no SQL appears outside `repository.py`.

**Application factory.** `create_app(config)` lets tests build an isolated
instance pointed at a temporary database, so tests never share state and can run
in any order.

**Connection lifecycle.** One connection is opened lazily per request and closed
on application-context teardown, which respects `sqlite3`'s
one-thread-per-connection rule without global state. The database runs in WAL
mode so reads are not blocked by a concurrent write, and writes go through
`with connection:` so a failure rolls back rather than committing halfway.

**Injection safety.** All values are bound as SQL parameters. `PATCH` builds its
`SET` clause dynamically, but the column names come from a fixed whitelist, so
nothing client-controlled is ever interpolated into a statement. A test asserts
that `?author=' OR 1=1 --` returns no rows.

**PUT versus PATCH.** `PUT` is a true replacement, per RFC 9110 — that is what
makes it idempotent, and it is why omitted optional fields are cleared. Because
partial updates are genuinely useful, `PATCH` is provided alongside it rather
than quietly redefining `PUT`.

**Unique ISBNs.** An ISBN identifies an edition, so the schema enforces
uniqueness with a partial index and the API answers `409 Conflict` on a
duplicate. The index is partial (`WHERE isbn IS NOT NULL`) so any number of
books may omit an ISBN.

**Lenient where it costs nothing.** Unknown fields in a body are ignored rather
than rejected, so a `GET` response can be round-tripped to `PUT`. A body is
parsed as JSON even without a `Content-Type: application/json` header. `year`
accepts `"1949"` as well as `1949`. Strictness is reserved for things that would
corrupt the collection.

**ISBN check digits are not validated.** Only length and type are checked. The
service stores identifiers supplied by its clients; rejecting an unusual but
legitimate one would be worse than storing it.

**No stack traces on the wire.** Unexpected exceptions are logged in full server
side and returned as a generic `500` body, so internal paths and SQL never leak.

---

## Project layout

```
.
├── app.py                    # Development entry point
├── bookapi/
│   ├── __init__.py           # create_app() application factory
│   ├── db.py                 # Connection lifecycle and schema
│   ├── errors.py             # Domain errors and JSON error handlers
│   ├── repository.py         # SQL for the books table
│   ├── routes.py             # HTTP endpoints
│   └── validation.py         # Request-body validation
├── tests/
│   ├── conftest.py           # App/client fixtures on a temp database
│   ├── test_books.py         # CRUD, listing, filtering
│   ├── test_errors.py        # JSON rendering of 404/405/413/500
│   ├── test_health.py        # Health check, healthy and degraded
│   ├── test_persistence.py   # Data survives restarts; commits land on disk
│   └── test_validation.py    # Field rules and malformed bodies
├── pyproject.toml            # pytest configuration
├── requirements.txt          # Runtime dependency
└── requirements-dev.txt      # Runtime + test dependencies
```
