# Book Collection API

A small REST API for managing a book collection: **Python + Flask + SQLite** (stdlib
`sqlite3`, no ORM).

## Requirements

- Python 3.9+ (developed and tested on 3.14)
- Flask 2.3+

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt      # or requirements.txt for runtime only
```

## Run

```bash
python wsgi.py                  # http://127.0.0.1:5000
```

Equivalent alternatives:

```bash
flask --app wsgi run            # add --debug for auto-reload
gunicorn wsgi:app               # if gunicorn is installed
```

Environment variables:

| Variable         | Default     | Meaning                                       |
| ---------------- | ----------- | --------------------------------------------- |
| `BOOKS_DB_PATH`  | `books.db`  | SQLite file. Created (with its parent dirs) on startup. |
| `HOST` / `PORT`  | `127.0.0.1` / `5000` | Bind address for `python wsgi.py`.   |
| `FLASK_DEBUG`    | unset       | `1` enables the debugger/reloader.            |

## Test

```bash
python -m pytest                # 110 tests
```

Each test gets a fresh SQLite file under pytest's `tmp_path`, so runs are isolated
and leave nothing behind.

The suite was checked by mutation testing — 25 deliberate defects (dropping the
author filter, never writing `updated_at`, removing each validation guard, making
`DELETE` always report success, reversing the list order, dropping the `Location`
header, …) were each caught by at least one failing test.

## API

Base URL `http://127.0.0.1:5000`. All request and response bodies are JSON.

### `GET /health`

Liveness *and* readiness — it runs a real query against SQLite.

```
200 {"status": "ok", "database": "ok"}
503 {"status": "error", "database": "unavailable", "detail": "..."}
```

### `POST /books`

Creates a book. `Content-Type: application/json` is required.

| Field    | Type            | Required | Notes                                     |
| -------- | --------------- | -------- | ----------------------------------------- |
| `title`  | string          | **yes**  | Trimmed; 1–500 chars.                     |
| `author` | string          | **yes**  | Trimmed; 1–255 chars.                     |
| `year`   | integer or null | no       | 1 – (current year + 5). A string of plain ASCII digits (`"1969"`) is accepted; anything `int()` would quietly misread — `"1_969"`, `"+1969"`, `"٣"` — is a `400`. |
| `isbn`   | string or null  | no       | Trimmed; ≤ 64 chars; unique across the collection. Blank becomes `null`. |

Text fields accept any UTF-8 — emoji, accents, non-Latin scripts — but reject NUL
bytes and unpaired surrogates, which SQLite cannot store.

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"9780441478125"}'
```

```
201 Created
Location: /books/1

{"id":1,"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin",
 "year":1969,"isbn":"9780441478125",
 "created_at":"2026-07-30T01:27:05.629590Z","updated_at":"2026-07-30T01:27:05.629590Z"}
```

### `GET /books`

Returns a JSON array ordered by `id` (insertion order); `[]` when empty.

`?author=` filters by **exact, case-insensitive** author match — a whole-name
match, not a substring. Surrounding whitespace is ignored, and a blank
`?author=` is treated as no filter.

```bash
curl --get --data-urlencode 'author=ursula k. le guin' http://127.0.0.1:5000/books
```

### `GET /books/{id}`

`200` with the book, or `404` if the id is unknown, not an integer, or outside the
64-bit range SQLite can store.

### `PUT /books/{id}`

**Full replacement**, per HTTP semantics: `title` and `author` are required, and
any omitted optional field is *cleared*. To keep the existing `year`/`isbn`, send
them back — a `GET` → edit → `PUT` round trip works directly, because the
server-owned fields (`id`, `created_at`, `updated_at`) are accepted and ignored.
An `id` in the body that contradicts the URL is a `400`, reported alongside any
other field errors rather than instead of them.

```bash
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974}'
```

`200` with the updated book, or `404` if the id is unknown.

### `DELETE /books/{id}`

`204 No Content` with an empty body, or `404` if the id is unknown (so deleting
twice reports the second attempt honestly rather than pretending to succeed).

## Status codes

| Code | When |
| ---- | ---- |
| `200` | Successful `GET` / `PUT`. |
| `201` | Book created; `Location` points at the new resource. |
| `204` | Book deleted. |
| `400` | Failed validation, malformed/empty JSON, or a body that is not a JSON object. |
| `404` | No such book, or no such route. |
| `405` | Wrong method for the route (the `Allow` header lists the right ones). |
| `409` | The `isbn` is already used by another book. |
| `413` | Request body larger than 64 KiB. |
| `415` | `Content-Type` on `POST`/`PUT` was not `application/json` or an RFC 6839 `+json` suffix type such as `application/hal+json`. |
| `500` | Unexpected server error (logged with a traceback). |
| `503` | `/health` could not reach the database. |

Errors always use one envelope — never HTML, even for Flask's own 404/405:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request body failed validation.",
    "fields": {
      "title": "title is required.",
      "year": "year must be an integer."
    }
  }
}
```

`fields` appears only on validation errors and lists **every** problem at once, so
a client can fix a whole form in one round trip.

## Layout

```
bookapi/
  __init__.py     create_app() — config, error handlers, blueprint, schema bootstrap
  db.py           SQLite connect/teardown, PRAGMAs, schema DDL
  repository.py   SQL for the books table (no Flask request needed)
  routes.py       HTTP endpoints
  validation.py   payload validation and cleaning
  errors.py       error types and the JSON error handlers
wsgi.py           entry point for python/flask/gunicorn
conftest.py       pytest fixtures
tests/            health, CRUD, author filter, validation
```

## Design notes

- **Framework choice.** The task left the framework open. FastAPI is present in
  this environment but unusable — it pulls in pydantic 1.10, which fails to
  import on Python 3.14 — so Flask (which works here) plus the standard-library
  `sqlite3` driver keeps the dependency list to one package.
- **Connection per request**, stored on Flask's `g` and closed on app-context
  teardown, so threaded servers never share a connection across threads. WAL mode
  lets reads proceed during a write. As a consequence the `DATABASE` setting must
  be a *file* — with `:memory:` each connection would get its own empty database.
- **Unique ISBNs are enforced by the database**, and the resulting
  `IntegrityError` is translated to `409`. There is no check-then-insert, so two
  concurrent writers cannot both slip the same ISBN through — 16 threads racing
  on one ISBN yield exactly one `201` and fifteen `409`s. A blank ISBN
  normalises to `NULL` rather than `""` — SQLite permits many `NULL`s in a unique
  column, so unlabelled books coexist while `""` would have collided on the
  second insert.
- **No ISBN checksum validation.** Length, type and uniqueness are checked, but
  the value is otherwise opaque, so pre-ISBN and internal catalogue identifiers
  are still storable.
- **Unknown fields are rejected** rather than silently dropped, which turns a
  typo like `"tittle"` into a clear `400` instead of a book with the wrong title.
- **Timestamps** are UTC, fixed-width (`%Y-%m-%dT%H:%M:%S.%fZ`), so lexical
  ordering matches chronological ordering.
- **All SQL is parameterised** — see `test_filter_does_not_allow_sql_injection`.
- **Request bodies are capped at 64 KiB** (`MAX_CONTENT_LENGTH`), so an oversized
  body is a `413` instead of unbounded buffering.
- **No client input reaches SQLite unchecked.** Several inputs would otherwise
  raise exceptions that are *not* `sqlite3.Error` and so escape as `500`s on what
  is really bad *client* input:

  | Input | Exception | Now |
  | ----- | --------- | --- |
  | id wider than 64 bits, `/books/99999999999999999999999999` | `OverflowError` | `404` |
  | unpaired surrogate, `{"title": "\ud800"}` (legal JSON) | `UnicodeEncodeError` | `400` |
  | body `{"id": "²"}` — `str.isdigit()` is True but `int()` refuses | `ValueError` | `400` |
  | DB parent directory not creatable | `OSError` (not caught by `/health`) | `503` |

  A fuzz sweep of 784 hostile requests across every verb, path and malformed body
  produces no `5xx`.
