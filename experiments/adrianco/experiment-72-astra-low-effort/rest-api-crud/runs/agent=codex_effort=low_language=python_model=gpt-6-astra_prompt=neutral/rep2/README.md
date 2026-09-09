# Book collection API

Python 3.10+ JSON REST service using standard-library WSGI and SQLite. No framework
was specified by the task or stack metadata; no runtime packages are required.

## Setup and run

```sh
python3 -m venv .venv
source .venv/bin/activate
python app.py
```

The service listens at http://127.0.0.1:8000. Set `HOST`, `PORT`, and `BOOKS_DB`
to override the listening address and database file (default: `books.db` in the
working directory). The database schema is created automatically; its parent
directory must exist. Use a file-backed database, not `:memory:`. The bundled
WSGI server is intended for local use.

```sh
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
```

## API

- `POST /books`: create a book; returns 201, the book, and a Location header.
- `GET /books`: return an array ordered by ID. Optional `author` is an exact,
  case-sensitive match; URL-encode the value.
- `GET /books/{id}`: return a book (200).
- `PUT /books/{id}`: replace all editable fields; return the updated book (200).
- `DELETE /books/{id}`: return `{"deleted":id}` (200).
- `GET /health`: check database connectivity; return `{"status":"ok"}` (200).

Books contain `id`, `title`, `author`, `year`, and `isbn`. Title and author must
be nonblank strings and are trimmed. Year is optional/null or a signed 64-bit
integer; ISBN is optional/null or a string (format is not restricted). PUT requires
title and author, and resets omitted optional fields to null. IDs are generated
by SQLite. Unknown fields are rejected. JSON bodies are limited to 1 MB.

Errors return `{"error":"message"}`: 400 for invalid input, 404 for missing
books/routes, 405 for unsupported methods, 413 for oversized bodies, 415 for
non-JSON content types, and 503 when SQLite is unavailable.

## Tests

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app.py test_app.py
```

Tests use isolated temporary SQLite files and exercise WSGI requests, CRUD,
validation, exact author filtering, SQL injection inputs, errors, health checks,
failed-update atomicity, and persistence across application instances.
