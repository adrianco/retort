# Book Collection API

A small REST API for managing a book collection. Built with Flask and stored in
SQLite (via Python's built-in `sqlite3` module).

## Requirements

- Python 3.10+

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

The server listens on `http://127.0.0.1:5000`. On macOS, port 5000 is often used
by AirPlay Receiver; if so, use `flask --app app run --port 5001` instead. The
database file defaults to
`books.db` in the current directory; override it with the `BOOKS_DB_PATH`
environment variable:

```bash
BOOKS_DB_PATH=/tmp/books.db python app.py
```

You can also use the Flask CLI:

```bash
flask --app app run
```

## Test

```bash
pytest
```

## API

Book fields:

| Field    | Type    | Required | Notes                              |
|----------|---------|----------|------------------------------------|
| `id`     | integer | —        | Assigned by the server             |
| `title`  | string  | yes      | Non-empty after trimming           |
| `author` | string  | yes      | Non-empty after trimming           |
| `year`   | integer | no       | Between 0 and next calendar year   |
| `isbn`   | string  | no       | Stored as given (trimmed)          |

| Method   | Path          | Success | Description                                  |
|----------|---------------|---------|----------------------------------------------|
| `GET`    | `/health`     | 200     | Health check: `{"status": "ok"}`             |
| `POST`   | `/books`      | 201     | Create a book. `Location` header is set.     |
| `GET`    | `/books`      | 200     | List all books. Supports `?author=` filter.  |
| `GET`    | `/books/{id}` | 200     | Get one book.                                |
| `PUT`    | `/books/{id}` | 200     | Replace a book's fields (full update).       |
| `DELETE` | `/books/{id}` | 204     | Delete a book.                               |

`?author=` matches the author name case-insensitively and exactly (not a substring match).

Errors are JSON:

- `400` — invalid body: `{"error": "validation failed", "details": {"<field>": "<message>"}}`
- `404` — unknown book or route: `{"error": "book not found"}`
- `405` — wrong HTTP method for a route

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

# List, filtered by author
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'

# Get one
curl http://127.0.0.1:5000/books/1

# Update (all fields are replaced)
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# Delete
curl -i -X DELETE http://127.0.0.1:5000/books/1
```

## Project layout

- `app.py` — application factory (`create_app`), validation, and routes
- `test_app.py` — pytest suite (endpoints, validation, error handling, persistence)
- `requirements.txt` — pinned dependencies
