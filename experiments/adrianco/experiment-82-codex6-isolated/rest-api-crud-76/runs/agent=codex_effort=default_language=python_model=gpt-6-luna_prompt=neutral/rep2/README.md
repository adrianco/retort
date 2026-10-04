# Book Collection API

A small REST API built with Python's standard library and SQLite. No third-party packages are required.

## Requirements

- Python 3.10 or newer

## Run

From this directory, start the server:

```sh
python app.py
```

The API listens at `http://127.0.0.1:8000`. Set `HOST` and `PORT` to change the bind address, and `BOOKS_DATABASE` to choose the SQLite database file. By default, the database is `books.db` in this directory.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book; JSON fields: `title` and `author` (required), `year` and `isbn` (optional)
- `GET /books` — list books; optionally filter with `?author=Name`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book; `title` and `author` are required, while `year` and `isbn` may be omitted or null
- `DELETE /books/{id}` — delete a book

Responses use JSON and standard HTTP status codes. Invalid input returns `400`, missing books return `404`, and a successful delete returns `204` with an empty body.

## Run tests

```sh
python -m unittest -v
```
