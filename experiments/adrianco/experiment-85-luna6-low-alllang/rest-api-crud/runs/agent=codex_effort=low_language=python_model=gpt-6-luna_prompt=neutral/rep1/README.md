# Books REST API

A dependency-free Python REST API for managing a book collection. It uses SQLite for persistent storage and Python's built-in HTTP server for HTTP handling.

## Requirements

- Python 3.10 or newer

## Run

```sh
python app.py
```

The server listens on `http://127.0.0.1:8000` and creates `books.db` in the current directory. Configure it with `BOOKS_HOST`, `BOOKS_PORT`, and `BOOKS_DATABASE` environment variables.

## API

- `GET /health` — health status
- `POST /books` — create a book with `title` and `author`; `year` and `isbn` are optional
- `GET /books` — list books; optionally filter with `?author=...`
- `GET /books/{id}` — fetch a book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Responses use JSON. Creating returns `201`, reads and updates return `200`, deletion returns `204`, malformed input returns `400`, and missing resources return `404`.

Example:

```sh
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

## Tests

```sh
python -m pytest
```
