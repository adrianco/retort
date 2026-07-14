# Book Collection REST API

A small REST API for managing a book collection, built with **Flask** and **SQLite** (Python standard library `sqlite3`, no ORM).

## Requirements

- Python 3.10+
- Flask and pytest (see `requirements.txt`)

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://127.0.0.1:5000`. Data is stored in `books.db` in the working directory (override with the `BOOKS_DB_PATH` environment variable).

## Endpoints

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book                                |
| GET    | `/books`      | List all books; filter with `?author=Name`   |
| GET    | `/books/{id}` | Get a single book                            |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}` | Delete a book                                |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

Validation errors return `400` with an `{"errors": [...]}` body. Missing books return `404`.

### Examples

```bash
# Create
curl -s -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List (optionally filtered by author)
curl -s 'http://127.0.0.1:5000/books?author=Frank%20Herbert'

# Get one
curl -s http://127.0.0.1:5000/books/1

# Update
curl -s -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -s -X DELETE http://127.0.0.1:5000/books/1 -o /dev/null -w '%{http_code}\n'
```

## Tests

```bash
python -m pytest -v
```

Tests use a temporary SQLite database per test, so they never touch `books.db`.
