# Book Collection API

A small Flask REST service backed by SQLite.

## Setup and run

Requires Python 3.10 or later.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server listens on `http://127.0.0.1:5000`. By default its SQLite database is
created at `instance/books.sqlite`. Set `BOOKS_DATABASE` to use another database path.

## API

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book and returns it with HTTP 201.
- `GET /books` lists books; `GET /books?author=Name` filters by author (case-insensitive exact match).
- `GET /books/{id}` retrieves a book.
- `PUT /books/{id}` updates supplied fields (title and author must remain non-empty).
- `DELETE /books/{id}` deletes a book and returns HTTP 204.

Book JSON fields are `title` and `author` (required), plus optional `year` (integer)
and `isbn` (string). Error responses are JSON and missing resources return HTTP 404.

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Tests

```bash
pytest
```
