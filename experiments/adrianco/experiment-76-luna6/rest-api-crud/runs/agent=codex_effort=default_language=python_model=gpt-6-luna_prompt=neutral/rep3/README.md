# Book Collection API

A small REST API written in Python using the standard-library HTTP server and SQLite. No third-party packages are required.

## Run

```sh
python3 app.py
```

The service listens on `http://127.0.0.1:8000`. Set `HOST` and `PORT` to change the bind address. By default it creates `books.db` beside `app.py`; set `BOOKS_DATABASE` to choose another SQLite file.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book; JSON fields: `title`, `author` (required), `year`, `isbn`
- `GET /books` — list books; optionally filter by exact author with `?author=Name`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book using the same fields as create
- `DELETE /books/{id}` — delete a book

Responses are JSON. Creation returns `201`, successful reads/updates return `200`, deletion returns `204`, invalid input returns `400`, and unknown routes or books return `404`.

Example:

```sh
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'
```

## Tests

Run the unit tests with:

```sh
python3 -m unittest -v
```
