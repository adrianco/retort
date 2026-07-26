# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (via Python's standard-library `sqlite3` module).

## Requirements

- Python 3.8+
- Flask (see `requirements.txt`)

## Setup

```bash
# (optional) create a virtual environment
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

## Running

```bash
python3 app.py
```

The service starts on `http://localhost:5000` and stores its data in a local
`books.db` SQLite file (created automatically on first request).

> **Note:** On macOS, port 5000 is often taken by the AirPlay Receiver. Set a
> different port with `PORT=5077 python3 app.py` (and adjust the URLs below).

## API

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check — returns `{"status":"ok"}` |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book                            |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book fields

| Field    | Type    | Required | Notes                    |
|----------|---------|----------|--------------------------|
| `title`  | string  | yes      | non-empty                |
| `author` | string  | yes      | non-empty                |
| `year`   | integer | no       |                          |
| `isbn`   | string  | no       |                          |

### Examples

```bash
# Create a book
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'

# List all books
curl http://localhost:5000/books

# Filter by author
curl 'http://localhost:5000/books?author=Andrew%20Hunt'

# Get one book
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2019}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation error (e.g. missing `title`/`author`)
- `404 Not Found` — book does not exist

## Tests

```bash
python3 -m pytest
```

The test suite (`test_app.py`) contains integration tests covering the health
check, creation, validation, retrieval, listing with author filtering,
updating, deletion, and 404 handling. Each test runs against an isolated
temporary SQLite database.
