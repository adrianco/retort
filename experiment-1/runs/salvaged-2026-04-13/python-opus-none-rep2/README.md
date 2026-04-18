# Books REST API

A simple Flask + SQLite REST API for managing a book collection.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://localhost:5000`. Set `PORT` or `BOOKS_DB` env vars to override the port or SQLite path.

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book. JSON body: `{"title", "author", "year", "isbn"}`. `title` and `author` are required.
- `GET /books` — list all books. Optional `?author=` filter.
- `GET /books/{id}` — get one book.
- `PUT /books/{id}` — update a book (partial updates supported).
- `DELETE /books/{id}` — delete a book.

## Tests

```bash
pytest
```
