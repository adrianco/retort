# Books API

A small REST API for managing a book collection, written in Python with
[Flask](https://flask.palletsprojects.com/) and the standard-library `sqlite3`
module for storage.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:5000`. Two environment variables are
honoured:

| Variable   | Default   | Meaning                       |
| ---------- | --------- | ----------------------------- |
| `DATABASE` | `books.db`| Path to the SQLite file       |
| `PORT`     | `5000`    | Port to bind                  |

The schema is created automatically on startup, so no migration step is needed.

Alternatively, via the Flask CLI:

```bash
flask --app app run
```

## Tests

```bash
python3 -m pytest
```

Tests use Flask's test client against a throwaway SQLite file in a temporary
directory, so they never touch your development database.

## API

All responses are JSON, except `DELETE`, which returns `204 No Content` with an
empty body.

### `GET /health`

```bash
curl localhost:5000/health
# 200 {"status": "ok"}
```

Executes a trivial query so a `200` means the database is reachable too.

### `POST /books`

Creates a book. `title` and `author` are required non-empty strings; `year`
(integer, 0–2200) and `isbn` (string) are optional.

```bash
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'
```

```json
201 {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

Invalid input returns `400` listing every problem found:

```json
400 {"error": "validation failed", "details": ["title is required", "year must be an integer"]}
```

### `GET /books`

Lists all books, ordered by id. Supports an optional `?author=` filter, which
matches case-insensitively on the whole author name.

```bash
curl 'localhost:5000/books?author=Frank%20Herbert'
# 200 [{"id": 1, ...}]
```

An unmatched filter returns `200` with an empty array.

### `GET /books/{id}`

```bash
curl localhost:5000/books/1
# 200 {"id": 1, ...}      404 {"error": "book not found"}
```

### `PUT /books/{id}`

Updates a book. Any subset of `title`, `author`, `year`, `isbn` may be sent;
omitted fields are left untouched. A supplied `title`/`author` must still be a
non-empty string, and an empty body is rejected with `400`.

```bash
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'
# 200 {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1966, ...}
```

### `DELETE /books/{id}`

```bash
curl -i -X DELETE localhost:5000/books/1
# 204 (empty body)        404 {"error": "book not found"}
```

## Status codes

| Code | When                                                       |
| ---- | ---------------------------------------------------------- |
| 200  | Successful `GET` / `PUT` / health check                     |
| 201  | Book created                                               |
| 204  | Book deleted                                               |
| 400  | Malformed JSON or failed validation                        |
| 404  | Unknown book id or unknown route                           |
| 405  | Method not allowed on a known route                        |

## Layout

| File           | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `app.py`       | Flask app factory, routes, validation                |
| `db.py`        | SQLite connection handling and schema                |
| `test_app.py`  | Integration tests covering every endpoint            |
