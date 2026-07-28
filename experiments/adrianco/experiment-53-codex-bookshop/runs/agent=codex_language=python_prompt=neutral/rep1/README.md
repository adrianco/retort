# Book Collection API

A small Flask REST API backed by SQLite.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

The service listens on `http://127.0.0.1:5000`. The database is `books.db` by default; set `BOOKS_DATABASE` to use another path.

## Endpoints

- `GET /health`
- `POST /books` with JSON `{ "title": "...", "author": "...", "year": 2024, "isbn": "..." }`
- `GET /books` (optionally `?author=...`)
- `GET /books/<id>`
- `PUT /books/<id>`
- `DELETE /books/<id>`

Title and author are required when creating a book. Updates may provide any subset of fields, but cannot clear title or author.

## Tests

```bash
pytest
```
