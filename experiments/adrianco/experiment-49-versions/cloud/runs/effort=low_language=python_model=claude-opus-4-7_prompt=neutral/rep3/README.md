# Books REST API

Flask + SQLite REST API for managing a book collection.

## Setup

```
pip install flask pytest
```

## Run

```
python app.py
```

Serves on `http://localhost:5000`. Override with `PORT` and `BOOKS_DB` env vars.

## Endpoints

- `GET /health` — health check
- `POST /books` — create book `{title, author, year?, isbn?}` (title & author required)
- `GET /books` — list books; optional `?author=Name` filter
- `GET /books/{id}` — get single book
- `PUT /books/{id}` — update book (partial fields allowed)
- `DELETE /books/{id}` — delete book

## Tests

```
pytest -v
```
