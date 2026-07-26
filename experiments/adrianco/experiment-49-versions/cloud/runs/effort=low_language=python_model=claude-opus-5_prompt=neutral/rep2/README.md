# Book Collection API

A small REST API for managing a book collection, built with **Flask** and **SQLite**.

## Requirements

- Python 3.9+
- Flask (`pip install flask`) — already present in this environment
- pytest, to run the tests

```bash
pip install flask pytest
```

## Running

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:5000` by default.

Environment variables:

| Variable   | Default   | Purpose                       |
|------------|-----------|-------------------------------|
| `PORT`     | `5000`    | Port to listen on             |
| `BOOKS_DB` | `books.db`| Path to the SQLite file       |

The database file and its schema are created automatically at startup.

## API

All responses are JSON (except `204 No Content` on delete).

### `GET /health`
Health check. Returns `200` with `{"status": "ok"}`.

### `POST /books`
Create a book. `title` and `author` are required non-empty strings; `year`
(integer) and `isbn` (string) are optional.

```bash
curl -X POST localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
```

- `201` — created, returns the book including its generated `id`
- `400` — validation failed, returns `{"errors": [...]}`

### `GET /books`
List all books, ordered by id. Optional `?author=` filter matches the author exactly.

```bash
curl 'localhost:5000/books?author=Frank%20Herbert'
```

- `200` — array of books (empty array if none match)

### `GET /books/{id}`
- `200` — the book
- `404` — `{"error": "book not found"}`

### `PUT /books/{id}`
Full replacement of the record — `title` and `author` are required, and any
omitted optional field (`year`, `isbn`) is reset to `null`.

```bash
curl -X PUT localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

- `200` — the updated book
- `400` — validation failed
- `404` — book does not exist

### `DELETE /books/{id}`
- `204` — deleted, empty body
- `404` — book does not exist

## Tests

```bash
python3 -m pytest -q
```

15 tests cover the health check, creation, validation failures, listing and the
author filter, fetch/update/delete including their 404 paths, and persistence
of updates. Each test runs against a fresh temporary SQLite database via the
`tmp_path` fixture, so tests are isolated and leave no files behind.

## Layout

| File           | Purpose                                          |
|----------------|--------------------------------------------------|
| `app.py`       | Flask application factory, routes, validation    |
| `db.py`        | SQLite connection helpers and schema             |
| `test_app.py`  | Integration tests exercising the HTTP API        |
