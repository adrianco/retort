# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.10+
- Flask
- pytest (for tests)

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://127.0.0.1:5000`. Data is stored in `books.db`
(override the path with the `BOOKS_DB` environment variable).

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book                                |
| GET    | `/books`      | List all books; filter with `?author=<name>` |
| GET    | `/books/{id}` | Get a single book                            |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}` | Delete a book                                |

A book has `title` (required string), `author` (required string),
`year` (optional integer), and `isbn` (optional string).

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Release It!", "author": "Michael Nygard", "year": 2018, "isbn": "978-1680502398"}'

# List (optionally filtered by author)
curl 'http://127.0.0.1:5000/books?author=Michael%20Nygard'

# Get one
curl http://127.0.0.1:5000/books/1

# Update
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 2019}'

# Delete
curl -X DELETE http://127.0.0.1:5000/books/1
```

### Status codes

- `200` — successful read/update
- `201` — book created
- `204` — book deleted
- `400` — validation error (missing/invalid fields, malformed JSON)
- `404` — book not found

## Tests

```bash
pytest
```

Tests run against a temporary database, so they never touch `books.db`.
