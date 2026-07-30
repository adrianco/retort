# Books API

A small REST service for managing a book collection. Python + Flask, with data stored
in SQLite via the standard-library `sqlite3` module.

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | Flask application, routing, validation |
| `db.py` | SQLite schema and data access |
| `test_app.py` | Integration tests driving the app through its HTTP interface |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py               # http://127.0.0.1:5000
PORT=8080 python3 app.py     # different port
BOOKS_DB=/tmp/my.db python3 app.py   # different database file
```

The database file (default `books.db` in the working directory) and its schema are
created automatically on startup.

## Tests

```bash
python3 -m pytest -q
```

Each test gets a fresh temporary database, so the suite never touches `books.db`.

## API

Base URL: `http://127.0.0.1:5000`. All responses are JSON except `204 No Content`.

### `GET /health`
`200` → `{"status": "ok"}` (also verifies the database is reachable).

### `POST /books`
Creates a book. `title` and `author` are required, non-empty strings. `year`
(integer, 0–2200) and `isbn` (string of 10 or 13 digits, dashes/spaces allowed) are
optional and default to `null`.

```bash
curl -X POST localhost:5000/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

`201` → the created book, including its assigned `id`.

### `GET /books`
`200` → array of books, ordered by `id`. Optional `?author=` filters by exact author
name, case-insensitively.

```bash
curl "localhost:5000/books?author=Frank%20Herbert"
```

### `GET /books/{id}`
`200` → the book, or `404` if no such book exists.

### `PUT /books/{id}`
Full replacement — the same validation rules as `POST` apply, and omitted optional
fields are reset to `null`.

```bash
curl -X PUT localhost:5000/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

`200` → the updated book. `404` if it does not exist, `400` if invalid.

### `DELETE /books/{id}`
`204` with an empty body on success, `404` if the book does not exist.

## Status codes

| Code | Meaning |
| --- | --- |
| `200` | Successful read or update |
| `201` | Book created |
| `204` | Book deleted |
| `400` | Missing/invalid body — see the `details` object for per-field messages |
| `404` | Unknown book or route |
| `405` | Method not allowed on that route |

Validation failures name every offending field at once:

```json
{
  "error": "validation failed",
  "details": {"title": "is required", "year": "must be an integer"}
}
```
