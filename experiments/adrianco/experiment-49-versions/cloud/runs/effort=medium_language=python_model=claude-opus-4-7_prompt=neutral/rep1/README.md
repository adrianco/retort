# Books REST API

A minimal REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask (`pip install flask`)

## Run

```
python3 app.py
```

The server listens on `http://localhost:5000` (override with `PORT`). The SQLite database is created at `books.db` in the current directory (override with `BOOKS_DB`).

## Endpoints

- `GET  /health` — health check
- `POST /books` — create a book. Body: `{"title": "...", "author": "...", "year": 2020, "isbn": "..."}`. `title` and `author` are required.
- `GET  /books` — list books. Supports `?author=NAME` filter.
- `GET  /books/{id}` — fetch a single book.
- `PUT  /books/{id}` — update a book (any subset of fields).
- `DELETE /books/{id}` — delete a book.

Responses are JSON. Status codes: `200` OK, `201` Created, `204` No Content, `400` Bad Request, `404` Not Found.

## Tests

```
python3 -m unittest -v
```
