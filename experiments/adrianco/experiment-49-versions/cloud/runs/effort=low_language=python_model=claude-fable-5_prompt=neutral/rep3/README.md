# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on http://localhost:5000. The SQLite database file defaults to
`books.db` (override with the `BOOKS_DB` environment variable).

## Endpoints

| Method | Path          | Description                                |
|--------|---------------|--------------------------------------------|
| GET    | /health       | Health check                               |
| POST   | /books        | Create a book (`title`, `author` required; optional `year`, `isbn`) |
| GET    | /books        | List books; filter with `?author=Name`     |
| GET    | /books/{id}   | Get one book                               |
| PUT    | /books/{id}   | Update a book (partial updates allowed)    |
| DELETE | /books/{id}   | Delete a book                              |

Example:

```bash
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
```

## Tests

```bash
pytest
```
