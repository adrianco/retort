# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask
- pytest (for tests)

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
(override the location with the `BOOKS_DB` environment variable).

## Run tests

```bash
python3 -m pytest -v
```

## Endpoints

| Method | Path          | Description                                   |
|--------|---------------|-----------------------------------------------|
| GET    | `/health`     | Health check                                  |
| POST   | `/books`      | Create a book                                 |
| GET    | `/books`      | List all books (optional `?author=` filter)   |
| GET    | `/books/{id}` | Get a single book                             |
| PUT    | `/books/{id}` | Update a book (partial updates supported)     |
| DELETE | `/books/{id}` | Delete a book                                 |

### Book fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer, optional)
- `isbn` (string, optional)

Validation errors return `400` with an `errors` array; missing books return
`404`; successful creation returns `201`; successful deletion returns `204`.

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List (filtered by author)
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'

# Get one
curl http://127.0.0.1:5000/books/1

# Update
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -X DELETE http://127.0.0.1:5000/books/1
```
