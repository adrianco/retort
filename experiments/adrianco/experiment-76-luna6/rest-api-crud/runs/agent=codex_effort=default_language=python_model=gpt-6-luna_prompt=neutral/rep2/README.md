# Book Collection API

A small Python WSGI REST service backed by SQLite. It uses only the Python standard library.

## Run

```sh
python app.py
```

The service listens on `http://localhost:8000`. Set `PORT` to change the port and `BOOKS_DATABASE` to choose the SQLite file (defaults to `books.sqlite3` in the current directory).

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with JSON fields `title` and `author` (required), and optional `year` and `isbn`
- `GET /books` — list books; optionally filter with `?author=Name`
- `GET /books/{id}` — retrieve a book
- `PUT /books/{id}` — replace book fields, requiring `title` and `author`
- `DELETE /books/{id}` — delete a book

Responses use JSON. Creation returns `201`, successful reads/updates return `200`, deletion returns `204`, invalid input returns `400`, and unknown books return `404`.

## Tests

```sh
python -m pytest
```
