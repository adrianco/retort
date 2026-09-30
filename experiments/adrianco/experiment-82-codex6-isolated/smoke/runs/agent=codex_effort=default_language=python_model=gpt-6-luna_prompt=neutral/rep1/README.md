# Book Collection API

A small REST API built with Python's standard library `http.server` and SQLite.
No third-party packages are required (Python 3.9+).

## Run

```sh
python app.py
```

The service listens at `http://127.0.0.1:8000`. Set `HOST`, `PORT`, or `BOOKS_DB`
to change the bind address, port, or SQLite database path.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with JSON `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books` — list books; optionally filter by exact author with `?author=...`
- `GET /books/{id}` — fetch a book
- `PUT /books/{id}` — replace a book's fields (title and author required; year and isbn optional)
- `DELETE /books/{id}` — delete a book

Title and author must be non-empty strings. Year must be an integer or null;
ISBN must be a string or null. Responses use JSON and standard HTTP status codes.

## Tests

```sh
python -m unittest -v
```
