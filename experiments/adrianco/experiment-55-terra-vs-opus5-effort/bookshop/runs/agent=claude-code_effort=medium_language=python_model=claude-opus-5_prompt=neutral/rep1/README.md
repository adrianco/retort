# Books API

A small REST service for managing a book collection, built with **Flask** and
**SQLite** (Python's stdlib `sqlite3` — no ORM, no external database).

## Layout

| File           | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `app.py`       | Application factory, validation, and route handlers  |
| `db.py`        | SQLite connection handling and schema bootstrap      |
| `test_app.py`  | Integration + unit tests (pytest)                    |

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py                       # http://127.0.0.1:5000
BOOKS_DB=/tmp/books.db PORT=8080 python app.py   # override db path / port
```

The SQLite file (`books.db` by default) and its schema are created on startup if
they don't already exist. For a production WSGI server, point it at the factory:

```bash
gunicorn 'app:create_app()'
```

## Tests

```bash
python -m pytest -q      # 25 tests, each against a fresh temporary database
```

## API

All responses are JSON, except `DELETE`, which returns an empty `204` body.

### `GET /health`

Liveness check; also verifies the database is reachable.

```json
{ "status": "ok", "database": "ok" }
```

### `POST /books`

Creates a book. `title` and `author` are **required** and must be non-empty
strings; `year` and `isbn` are optional and default to `null`.

```bash
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

`201 Created`, with a `Location: /books/{id}` header:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

### `GET /books`

Lists all books ordered by `id`, as a JSON array. Supports an optional
`?author=` filter (exact match, case-insensitive).

```bash
curl 'localhost:5000/books'
curl 'localhost:5000/books?author=Frank%20Herbert'
```

### `GET /books/{id}`

Returns a single book, or `404` if it doesn't exist.

### `PUT /books/{id}`

Full replacement of the resource — `title` and `author` are required, and any
optional field you omit is reset to `null`. Returns the updated book, or `404`.

```bash
curl -X PUT localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1984}'
```

### `DELETE /books/{id}`

`204 No Content` on success, `404` if the book doesn't exist.

## Validation and status codes

| Code  | When                                                              |
| ----- | ----------------------------------------------------------------- |
| `200` | Successful `GET` / `PUT`                                          |
| `201` | Book created                                                      |
| `204` | Book deleted                                                      |
| `400` | Missing/blank `title` or `author`, bad `year`, unknown field, or a missing/malformed JSON body |
| `404` | No book with the given id, or unknown route                       |
| `405` | Method not allowed on a known route                               |

Validation errors name every offending field at once:

```json
{
  "error": "Validation failed",
  "details": { "title": "must be a non-empty string", "year": "must be an integer or null" }
}
```

Rules enforced:

- `title`, `author` — required, non-empty after trimming whitespace (which is
  also stripped before storing).
- `year` — integer between 0 and 2200, or `null`.
- `isbn` — string or `null`; an empty string is normalised to `null`. The format
  is not checked.
- Unknown fields are rejected rather than silently ignored.
