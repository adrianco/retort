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

Server runs at `http://localhost:5000`. Database file: `books.db` (override via `BOOKS_DB` env var).

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book. JSON: `{title, author, year?, isbn?}`. `title` and `author` are required.
- `GET /books` — list all books; supports `?author=Name` filter
- `GET /books/{id}` — get one book
- `PUT /books/{id}` — update a book (partial updates allowed)
- `DELETE /books/{id}` — delete a book

## Test

```bash
pytest -v
```
