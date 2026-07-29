# Book Collection API

A small REST API implemented with Flask and SQLite.

## Setup and run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

The service listens on `http://127.0.0.1:5000`. Set `DATABASE` to change the
SQLite file location, for example `DATABASE=/tmp/books.db python3 app.py`.

## Endpoints

- `GET /health` — health check
- `POST /books` — create a book; JSON must contain non-empty `title` and `author`
- `GET /books?author=...` — list books, optionally filtering by author
- `GET /books/<id>` — retrieve one book
- `PUT /books/<id>` — update any supplied fields (`title`, `author`, `year`, `isbn`)
- `DELETE /books/<id>` — delete a book

Example request body:

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

## Tests

```bash
pytest -q
```
