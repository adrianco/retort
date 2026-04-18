# Book Collection API

A simple Flask REST API for managing a book collection, backed by SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on port 5000 by default (override with `PORT`). The SQLite
database file defaults to `books.db` (override with `DB_PATH`).

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book (JSON: `title`, `author`, optional `year`, `isbn`)
- `GET /books` — list all books (optional `?author=` filter)
- `GET /books/{id}` — get one book
- `PUT /books/{id}` — update a book
- `DELETE /books/{id}` — delete a book

`title` and `author` are required and must be non-empty strings.

## Tests

```bash
pytest
```
