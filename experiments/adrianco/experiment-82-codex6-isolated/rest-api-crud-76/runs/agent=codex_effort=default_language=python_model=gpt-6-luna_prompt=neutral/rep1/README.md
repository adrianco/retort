# Books API

A small REST API for managing books. It uses only the Python standard library, WSGI, and SQLite.

## Requirements

Python 3.9 or newer. No third-party packages are required.

## Run

```sh
python app.py
```

The service listens on `http://localhost:8000`. It creates `books.db` in the current directory. Set `PORT` to change the port and `BOOKS_DB` to choose a different SQLite file.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book using JSON with `title`, `author`, and optional `year` and `isbn`
- `GET /books` — list books; `?author=Name` filters by exact author name
- `GET /books/{id}` — fetch a book
- `PUT /books/{id}` — replace a book; provide `title` and `author`, with optional `year` and `isbn`
- `DELETE /books/{id}` — delete a book

Create and update requests return `400` for malformed JSON or invalid fields. Successful creation returns `201`; successful deletion returns `204`. Missing books return `404`.

## Test

```sh
python -m unittest -v
```
