# Book Collection API

A small REST API built with Python's standard library and SQLite. It runs as a WSGI service and requires Python 3.9 or newer; no third-party packages are needed.

## Run

```sh
python app.py
```

The service listens on `http://127.0.0.1:8000`. Set `PORT` to change the port and `BOOKS_DB_PATH` to choose the SQLite database file (defaults to `books.db` in this directory).

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with JSON `title`, `author`, and optional `year`, `isbn`
- `GET /books` — list books; optionally filter with `?author=...`
- `GET /books/{id}` — fetch a book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Responses use JSON. Invalid required fields return `400`, missing books return `404`, successful creation returns `201`, and deletion returns `204`.

## Test

```sh
python -m pytest
```
