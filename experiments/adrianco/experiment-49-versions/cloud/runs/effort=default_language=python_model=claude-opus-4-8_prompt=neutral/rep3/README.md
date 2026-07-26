# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (via Python's stdlib `sqlite3`).

## Requirements

- Python 3.9+
- Flask, pytest (see `requirements.txt`)

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

The server listens on `http://localhost:5000`. Data is persisted to a
`books.db` SQLite file created next to `app.py` on first run.

## Endpoints

| Method | Path            | Description                                  |
|--------|-----------------|----------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`            |
| POST   | `/books`        | Create a book                                |
| GET    | `/books`        | List all books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Get a single book                            |
| PUT    | `/books/{id}`   | Update a book (any subset of fields)         |
| DELETE | `/books/{id}`   | Delete a book                                |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Status codes

- `200` OK, `201` Created, `204` No Content (delete)
- `400` Bad Request (validation failure)
- `404` Not Found

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0261102217"}'

# List / filter
curl http://localhost:5000/books
curl 'http://localhost:5000/books?author=J.R.R.%20Tolkien'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' -d '{"year": 1951}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

## Tests

```bash
pytest
```
