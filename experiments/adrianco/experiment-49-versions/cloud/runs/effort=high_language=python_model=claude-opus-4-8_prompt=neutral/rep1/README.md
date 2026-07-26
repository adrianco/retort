# Book Collection API

A small REST API for managing a collection of books, built with **Flask** and
backed by **SQLite** (via the standard-library `sqlite3` module).

## Features

- Full CRUD for books (`title`, `author`, `year`, `isbn`)
- Filter the book list by author
- Input validation (`title` and `author` are required and must be non-blank)
- JSON responses with appropriate HTTP status codes
- Health check endpoint

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Setup

```bash
# (optional) create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Running

```bash
# Option 1: run the module directly (serves on port 8000)
python3 app.py

# Option 2: use the Flask CLI
flask --app app run --port 8000
```

The SQLite database file defaults to `books.db` in the current directory. Set
the `BOOKS_DB_PATH` environment variable to change its location:

```bash
BOOKS_DB_PATH=/path/to/mybooks.db python3 app.py
```

## API

Base URL: `http://localhost:8000`

| Method | Path            | Description                              | Success code |
|--------|-----------------|------------------------------------------|--------------|
| GET    | `/health`       | Health check                             | 200          |
| POST   | `/books`        | Create a book                            | 201          |
| GET    | `/books`        | List books (optional `?author=` filter)  | 200          |
| GET    | `/books/{id}`   | Get a single book                        | 200          |
| PUT    | `/books/{id}`   | Update a book                            | 200          |
| DELETE | `/books/{id}`   | Delete a book                            | 200          |

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are
optional.

### Status codes

- `201 Created` — book successfully created
- `200 OK` — successful read/update/delete
- `400 Bad Request` — validation failed (e.g. missing `title`/`author`)
- `404 Not Found` — no book with the given id

### Examples

```bash
# Create
curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all
curl http://localhost:8000/books

# Filter by author
curl 'http://localhost:8000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:8000/books/1

# Update
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://localhost:8000/books/1
```

## Testing

```bash
python3 -m pytest
```

The test suite (`test_app.py`) covers the health check, create/read, validation
errors, author filtering, update, delete, and 404 handling. Each test uses a
fresh temporary database so runs are isolated and repeatable.
