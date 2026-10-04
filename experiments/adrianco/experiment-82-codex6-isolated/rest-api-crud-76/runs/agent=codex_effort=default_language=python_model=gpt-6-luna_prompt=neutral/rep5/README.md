# Book Collection API

A small REST API written in Python using only the standard library. Book data is persisted in SQLite.

## Requirements

Python 3.9 or newer.

## Run

```sh
python app.py
```

The service listens on `http://127.0.0.1:8000`. Set `HOST`, `PORT`, or `BOOKS_DB` to change the bind address, port, or database file.

## Endpoints

- `GET /health` — health status.
- `POST /books` — create a book with JSON fields `title`, `author`, and optional `year`, `isbn`.
- `GET /books` — list books; `?author=...` filters author names (case-insensitive substring).
- `GET /books/{id}` — retrieve a book.
- `PUT /books/{id}` — replace book fields; `title` and `author` are required.
- `DELETE /books/{id}` — delete a book.

Responses use JSON. Invalid input returns `400`, missing books return `404`, creation returns `201`, and deletion returns `204`.

## Tests

```sh
python -m unittest -v
```
