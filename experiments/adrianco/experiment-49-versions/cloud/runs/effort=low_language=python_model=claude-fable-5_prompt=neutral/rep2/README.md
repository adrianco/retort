# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts at http://127.0.0.1:5000. Data is stored in `books.db` (created automatically).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET | /books | List books; filter with `?author=Name` |
| GET | /books/{id} | Get a book |
| PUT | /books/{id} | Update a book (partial updates allowed) |
| DELETE | /books/{id} | Delete a book |

Example:

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
```

## Tests

```bash
pytest
```
