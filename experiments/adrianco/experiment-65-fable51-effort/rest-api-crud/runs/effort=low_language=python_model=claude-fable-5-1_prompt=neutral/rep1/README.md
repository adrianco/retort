# Book Collection API

A small REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://localhost:5000`. Set `PORT` to change the port and
`BOOKS_DB` to change the SQLite file path (default `books.db`, created automatically).

## Endpoints

| Method | Path              | Description                                   |
|--------|-------------------|-----------------------------------------------|
| GET    | `/health`         | Health check, returns `{"status": "ok"}`      |
| POST   | `/books`          | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`          | List books, optional `?author=` exact filter  |
| GET    | `/books/{id}`     | Get one book                                  |
| PUT    | `/books/{id}`     | Update any subset of fields                   |
| DELETE | `/books/{id}`     | Delete a book (204 on success)                |

Validation failures return `400` with `{"errors": [...]}`; missing books return `404`.

Example:

```bash
curl -X POST localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
```

## Tests

```bash
pytest
```
