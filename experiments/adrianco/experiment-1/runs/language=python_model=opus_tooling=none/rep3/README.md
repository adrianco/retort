# Books API

A simple REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://0.0.0.0:5000`. Data is stored in `books.db` (override with the `BOOKS_DB` environment variable).

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book. JSON body: `{"title", "author", "year", "isbn"}`. `title` and `author` are required.
- `GET /books` — list all books. Optional `?author=<name>` filter.
- `GET /books/{id}` — fetch a single book.
- `PUT /books/{id}` — update a book (partial updates allowed).
- `DELETE /books/{id}` — delete a book.

## Tests

```bash
pytest
```
