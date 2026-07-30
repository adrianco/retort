# Books API

A small REST service for managing a book collection, built with **Flask** and the
standard library's **sqlite3** module.

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | Routes, validation, and the `create_app()` factory |
| `db.py` | SQLite connection handling and schema creation |
| `test_app.py` | Integration tests driven through Flask's test client |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
flask --app app run          # http://127.0.0.1:5000
```

Or directly:

```bash
python app.py               # honours PORT, default 5000
```

The SQLite file is created on startup if it does not exist. It defaults to
`books.db` in the working directory; override it with the `DATABASE`
environment variable:

```bash
DATABASE=/var/lib/books/books.db flask --app app run
```

## Tests

```bash
python -m pytest -q
```

Each test gets a fresh SQLite file in a pytest `tmp_path`, so runs are isolated
and leave nothing behind.

## API

All responses are JSON, except `DELETE`, which returns an empty `204`.

### `GET /health`

Liveness plus a `SELECT 1` against the database.

```json
{ "status": "ok", "database": "ok" }
```

Returns `503` with `"database": "unavailable"` if the database cannot be queried.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are optional.

```bash
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

`201 Created`, with a `Location: /books/1` header:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

### `GET /books`

Lists all books in `id` order. Optional `?author=` filter matches the full author
name, case-insensitively, ignoring surrounding whitespace.

```bash
curl 'localhost:5000/books?author=frank+herbert'
```

An unmatched filter is an empty list (`200`), not a `404`.

### `GET /books/{id}`

Returns one book, or `404` if the id is unknown.

### `PUT /books/{id}`

A **full replacement**: the same validation rules as `POST` apply, and any
optional field you omit is cleared to `null`.

```bash
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

Returns `200` with the updated book, or `404` if the id is unknown.

### `DELETE /books/{id}`

Returns `204` with an empty body, or `404` if the id is unknown.

## Validation and status codes

| Status | When |
| --- | --- |
| `200` | Successful `GET` / `PUT` |
| `201` | Book created |
| `204` | Book deleted |
| `400` | Validation failed, or the body is not a JSON object / is malformed JSON |
| `404` | No book with that id, or unknown route |
| `405` | Method not allowed on that route |
| `503` | Database unreachable (`/health` only) |

Rules enforced on `POST` and `PUT`:

- `title` and `author` — required, must be non-empty strings; surrounding
  whitespace is trimmed before storing
- `year` — optional integer between -3000 and 2200 (booleans rejected)
- `isbn` — optional string, stored trimmed

Errors carry a consistent shape, with `details` listing every problem found
rather than only the first:

```json
{ "error": "Validation failed", "details": ["title is required", "year must be an integer"] }
```

Error responses are JSON for *all* failures, including framework-generated ones
such as unknown routes, so clients never have to parse Flask's HTML error pages.

## Notes and limitations

- `id` is a SQLite `AUTOINCREMENT` primary key and is assigned by the server;
  any `id` in a request body is ignored.
- Duplicate ISBNs are permitted — the same book can legitimately appear twice in
  a collection, and the task specifies no uniqueness constraint.
- The connection is request-scoped (Flask's `g`) and closed on teardown, so the
  development server's threaded mode is safe. For production use, put this
  behind a WSGI server such as gunicorn.
