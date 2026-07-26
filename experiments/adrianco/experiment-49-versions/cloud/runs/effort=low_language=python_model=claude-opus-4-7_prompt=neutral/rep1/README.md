# Books API

A small REST API for managing a book collection, built with Flask + SQLite.

## Setup

```bash
pip install flask pytest
```

## Run

```bash
python app.py
# listens on http://localhost:5000
```

Set `PORT` or `BOOKS_DB` env vars to override defaults.

## Endpoints

- `GET  /health` — health check
- `POST /books` — create `{title, author, year?, isbn?}` (title & author required)
- `GET  /books` — list all; `?author=Name` filters by author
- `GET  /books/{id}` — fetch one
- `PUT  /books/{id}` — partial update
- `DELETE /books/{id}` — delete

Returns JSON, standard HTTP codes (200/201/204/400/404).

## Tests

```bash
pytest -v
```
