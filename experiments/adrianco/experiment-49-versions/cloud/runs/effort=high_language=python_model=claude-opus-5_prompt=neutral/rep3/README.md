# Book Collection API

A small REST service for managing a book collection, built with **Flask** and the
standard library's **sqlite3** module. No ORM, no code generation — the whole
service is about 300 lines.

## Requirements

- Python 3.9+
- Flask 2.3+ (the only runtime dependency; SQLite ships with Python)

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

The service listens on <http://127.0.0.1:8000> and creates `books.db` in the
working directory on first start. Override any of these with environment
variables:

| Variable   | Default     | Purpose                          |
|------------|-------------|----------------------------------|
| `BOOKS_DB` | `books.db`  | Path to the SQLite database file |
| `HOST`     | `127.0.0.1` | Bind address                     |
| `PORT`     | `8000`      | Bind port                        |
| `DEBUG`    | unset       | Set to `1` for the Flask reloader |

`app.py` also exposes a module-level `app`, so any WSGI server works:

```bash
flask --app app run --port 8000     # Flask's dev server
gunicorn app:app                    # production-style (pip install gunicorn)
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

36 tests cover every endpoint plus validation, filtering, error handling, and
persistence across a restart. Each test runs against its own throwaway SQLite
file, so the suite never touches your `books.db`.

## API

All responses are JSON, including errors. `POST` and `PUT` require
`Content-Type: application/json`.

| Method   | Path           | Success | Notes                                     |
|----------|----------------|---------|-------------------------------------------|
| `GET`    | `/health`      | 200     | Also pings the database                   |
| `POST`   | `/books`       | 201     | Returns the new book and a `Location` header |
| `GET`    | `/books`       | 200     | JSON array; `?author=` filters            |
| `GET`    | `/books/{id}`  | 200     |                                           |
| `PUT`    | `/books/{id}`  | 200     | Full replacement — see below              |
| `DELETE` | `/books/{id}`  | 204     | Empty body                                |

### Book fields

| Field        | Type   | Required | Notes                                          |
|--------------|--------|----------|------------------------------------------------|
| `title`      | string | **yes**  | Non-empty after trimming, ≤ 255 characters      |
| `author`     | string | **yes**  | Non-empty after trimming, ≤ 255 characters      |
| `year`       | int    | no       | Between 1 and next year                        |
| `isbn`       | string | no       | Valid ISBN-10 or ISBN-13, unique across the collection |
| `id`         | int    | —        | Server-assigned                                 |
| `created_at` | string | —        | Server-assigned, ISO 8601 UTC                   |
| `updated_at` | string | —        | Server-assigned, ISO 8601 UTC                   |

Unknown fields in a request body are ignored, so a book you read from the API
can be sent straight back to it without stripping `id` or the timestamps.

### Examples

```bash
# Create
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}'

# List, and filter by author
curl localhost:8000/books
curl 'localhost:8000/books?author=orwell'

# Read, replace, delete
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'
curl -X DELETE localhost:8000/books/1
```

### Errors

Every failure uses the same shape, with `details` present only for validation
problems:

```json
{
  "error": "validation_failed",
  "message": "The request body failed validation.",
  "details": {"title": "is required", "year": "must be an integer"}
}
```

| Status | When                                                            |
|--------|-----------------------------------------------------------------|
| 400    | Validation failed, or the body is not a JSON object              |
| 404    | No book with that id, or unknown route                           |
| 405    | Method not supported on that path                                |
| 409    | The ISBN already belongs to another book                         |
| 415    | Body was not sent as `application/json`                          |
| 500    | Unexpected server error (logged with a traceback)                |

All problems with a payload are reported in one response rather than one per
request, so a client can fix everything in a single round trip.

## Design notes

**PUT replaces the whole resource.** Omitting `year` or `isbn` clears them,
which is what PUT means in HTTP. There is deliberately no PATCH endpoint; add
one if partial updates are needed.

**ISBNs are validated by check digit, not just by shape.** The trailing digit
of an ISBN exists to catch typos and transpositions, so the service verifies it
and reports "the check digit does not match" separately from "wrong number of
digits". This does reject strings that look plausible — `978-0-261-10221-4` is
refused because the real ISBN ends in `7`. Hyphens and spaces are ignored, and
the normalised digits are what get stored and returned.

**`?author=` is a case-insensitive substring match**, so `?author=orwell` finds
"George Orwell". SQL `LIKE` wildcards in the query are escaped and matched
literally.

**One connection per request.** `bookapi/db.py` opens a SQLite connection per
Flask application context and closes it on teardown, so requests never share a
connection. Uniqueness of ISBNs is enforced by a `UNIQUE` constraint in the
schema rather than a read-then-write check, which would race under concurrency.

## Layout

```
app.py                     entry point (module-level `app`, plus `__main__`)
bookapi/
  __init__.py              application factory
  db.py                    connection lifecycle and schema
  validation.py            payload validation and normalisation
  repository.py            SQL for the books table
  routes.py                HTTP layer
  errors.py                ApiError plus JSON error handlers
tests/
  conftest.py              fixtures: temp-file database per test
  test_books_api.py        36 tests through Flask's test client
```
