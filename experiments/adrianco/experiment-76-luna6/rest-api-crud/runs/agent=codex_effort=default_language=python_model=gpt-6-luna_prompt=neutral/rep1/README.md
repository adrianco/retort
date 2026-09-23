# Book Collection API

A small JSON REST API for managing books, backed by SQLite and built with Python's standard library.

## Requirements

Python 3.9 or newer. No third-party packages are required.

## Run

```sh
python app.py
```

The service listens on `http://localhost:8000`. Set `PORT` to change the port and `BOOKS_DB` to choose the SQLite database path (defaults to `books.sqlite3` in the current directory).

## Endpoints

- `GET /health` — health status.
- `POST /books` — create a book from JSON with required `title` and `author`, and optional `year` and `isbn`.
- `GET /books` — list books; add `?author=Name` to filter by exact author.
- `GET /books/{id}` — fetch a book.
- `PUT /books/{id}` — replace a book using the same JSON shape as creation.
- `DELETE /books/{id}` — delete a book.

Responses are JSON. Creates return `201`, deletes return `204`, invalid JSON or fields return `400`, and missing books return `404`.

Example:

```sh
curl -i -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Tests

```sh
python -m unittest -v
```
