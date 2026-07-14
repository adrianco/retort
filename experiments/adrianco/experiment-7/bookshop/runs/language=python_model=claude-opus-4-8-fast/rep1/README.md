# Book Collection API

A small REST API for managing a book collection, built with **FastAPI** and **SQLite**.

## Features

- Full CRUD for books (`title`, `author`, `year`, `isbn`)
- List with optional `?author=` filter
- Input validation (`title` and `author` are required and non-blank)
- JSON responses with appropriate HTTP status codes
- Health check endpoint

## Requirements

- Python 3.10+

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The service listens on `http://127.0.0.1:8000`.
Interactive API docs are available at `http://127.0.0.1:8000/docs`.

By default data is stored in `books.db` in the current directory. Override the
location with the `BOOKS_DB_PATH` environment variable:

```bash
BOOKS_DB_PATH=/path/to/mybooks.db uvicorn main:app
```

## API

| Method | Path           | Description                          | Success status |
|--------|----------------|--------------------------------------|----------------|
| GET    | `/health`      | Health check                         | 200            |
| POST   | `/books`       | Create a book                        | 201            |
| GET    | `/books`       | List books (optional `?author=`)     | 200            |
| GET    | `/books/{id}`  | Get a single book                    | 200            |
| PUT    | `/books/{id}`  | Update a book                        | 200            |
| DELETE | `/books/{id}`  | Delete a book                        | 204            |

Validation errors return `422`; unknown IDs return `404`.

### Example

```bash
# Create
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List by author
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Get one
curl http://127.0.0.1:8000/books/1

# Update
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE http://127.0.0.1:8000/books/1
```

## Tests

```bash
pytest
```

The suite (`test_main.py`) covers health, create/get, validation, filtering,
update, delete, and 404 handling using an isolated temporary database.

## Project layout

```
main.py            FastAPI app and routes
db.py              SQLite persistence layer
test_main.py       Integration tests
requirements.txt   Dependencies
```
