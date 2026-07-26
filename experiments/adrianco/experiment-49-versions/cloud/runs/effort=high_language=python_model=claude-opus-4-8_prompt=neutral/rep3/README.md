# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite**.

## Features

- Create, read, update, and delete books
- List books with optional filtering by author
- Input validation (`title` and `author` are required)
- JSON responses with appropriate HTTP status codes
- Health check endpoint

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Setup

```bash
# (optional) create a virtual environment
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

## Running

```bash
python3 app.py
```

The service starts on `http://localhost:5000` and stores data in a local
SQLite file named `books.db` (created automatically on first run).

> **macOS note:** port 5000 is often used by the AirPlay Receiver. If you see
> "Address already in use", either disable AirPlay Receiver in System Settings
> or run on another port:
> `python3 -c "from app import create_app; create_app().run(port=5055)"`

## API Reference

| Method | Path            | Description                                   |
|--------|-----------------|-----------------------------------------------|
| GET    | `/health`       | Health check — returns `{"status": "ok"}`     |
| POST   | `/books`        | Create a new book                             |
| GET    | `/books`        | List all books (supports `?author=` filter)   |
| GET    | `/books/{id}`   | Get a single book by ID                       |
| PUT    | `/books/{id}`   | Update a book (partial updates allowed)       |
| DELETE | `/books/{id}`   | Delete a book                                 |

### Book object

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required and must be non-empty strings. `year`
(integer) and `isbn` (string) are optional.

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation failed or malformed JSON
- `404 Not Found` — book does not exist

### Examples

```bash
# Create a book
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "year": 1999, "isbn": "978-0201616224"}'

# List all books
curl http://localhost:5000/books

# Filter by author
curl "http://localhost:5000/books?author=Andrew%20Hunt"

# Get one book
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 2000}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```

## Testing

```bash
python3 -m pytest
```

The test suite (`test_app.py`) uses a temporary throwaway SQLite database per
test and covers the health check, CRUD operations, author filtering, and input
validation.
