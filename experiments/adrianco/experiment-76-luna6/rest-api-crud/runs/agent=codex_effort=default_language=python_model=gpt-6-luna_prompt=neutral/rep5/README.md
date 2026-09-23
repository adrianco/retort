# Book Collection API

A JSON REST API implemented with Python's standard-library WSGI server and SQLite. It has no third-party runtime dependencies.

## Run

Use Python 3.10 or newer:

```sh
python app.py
```

The API listens on `http://127.0.0.1:8000`. SQLite data is stored in `books.db` in the current directory. Set `BOOKS_DATABASE=/path/to/file.sqlite` to choose another database.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with JSON `title`, `author`, and optional `year`, `isbn`
- `GET /books` — list books; optional exact-match `?author=...` filter
- `GET /books/{id}` — retrieve a book
- `PUT /books/{id}` — update supplied fields (title and author must remain non-empty)
- `DELETE /books/{id}` — delete a book

Errors are JSON. Missing books return `404`, invalid input returns `400`, and successful creation returns `201`.

## Tests

```sh
python -m unittest -v
```
