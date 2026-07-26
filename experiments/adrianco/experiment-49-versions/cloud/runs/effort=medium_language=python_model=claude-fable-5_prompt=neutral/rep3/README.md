# Book Collection REST API

A small Flask + SQLite service for managing a book collection.

## Requirements

- Python 3.9+
- Flask, pytest (see `requirements.txt`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:5000`. Data is stored in `books.db`
(override with the `BOOKS_DB` environment variable).

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — `{"status": "ok"}`            |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List all books; filter with `?author=Name`   |
| GET    | `/books/{id}` | Get one book                                 |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}` | Delete a book (returns 204)                  |

Validation errors return `400` with an `errors` list; missing books return `404`.

### Example

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'
```

## Tests

```bash
pytest
```
