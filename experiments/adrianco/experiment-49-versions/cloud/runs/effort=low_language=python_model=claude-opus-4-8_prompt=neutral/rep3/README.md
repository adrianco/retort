# Book Collection API

A small REST API for managing a book collection, built with **Flask** and the
standard-library **`sqlite3`** module.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on `http://localhost:5000`. Data is stored in a local
`books.db` SQLite file (created automatically on first run).

## Run the tests

```bash
python3 -m pytest
```

Tests use an in-memory SQLite database, so they don't touch `books.db`.

## Endpoints

| Method | Path            | Description                                   |
|--------|-----------------|-----------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`             |
| POST   | `/books`        | Create a book                                 |
| GET    | `/books`        | List all books (optional `?author=` filter)   |
| GET    | `/books/{id}`   | Get a single book                             |
| PUT    | `/books/{id}`   | Update a book                                  |
| DELETE | `/books/{id}`   | Delete a book                                  |

### Book fields

- `title` — string, **required**
- `author` — string, **required**
- `year` — integer, optional
- `isbn` — string, optional

### Status codes

- `200` OK, `201` Created, `204` No Content (delete)
- `400` Bad Request (validation error — missing/empty `title` or `author`)
- `404` Not Found

## Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List (filtered by author)
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1965}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```
