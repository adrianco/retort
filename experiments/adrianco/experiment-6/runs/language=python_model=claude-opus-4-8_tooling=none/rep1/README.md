# Book Collection API

A small REST API for managing a book collection, built with **Python's standard
library only** (`http.server` + `sqlite3`). No external dependencies or package
manager required.

## Requirements

- Python 3.7+

## Run

```bash
python3 app.py
```

The server starts on `http://127.0.0.1:8000` and stores data in a local
`books.db` SQLite file (created automatically on first run).

## Test

```bash
python3 -m unittest test_app -v
```

The test suite spins up the real HTTP server on an ephemeral port backed by a
temporary database and exercises every endpoint over HTTP.

## API

A book has the fields: `id` (auto), `title`, `author`, `year`, `isbn`.
`title` and `author` are required; `year` (integer) and `isbn` (string) are
optional.

| Method | Path            | Description                                   |
|--------|-----------------|-----------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`             |
| POST   | `/books`        | Create a book                                 |
| GET    | `/books`        | List all books (optional `?author=` filter)   |
| GET    | `/books/{id}`   | Get a single book                             |
| PUT    | `/books/{id}`   | Update a book                                  |
| DELETE | `/books/{id}`   | Delete a book                                  |

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid / missing JSON or failed validation
- `404 Not Found` — unknown route or missing book

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "year": 1999, "isbn": "978-0201616224"}'

# List, filtered by author
curl 'http://127.0.0.1:8000/books?author=Andrew%20Hunt'

# Get one
curl http://127.0.0.1:8000/books/1

# Update
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Pragmatic Programmer (2nd ed.)", "author": "Andrew Hunt", "year": 2019}'

# Delete
curl -X DELETE http://127.0.0.1:8000/books/1
```

## Files

- `app.py` — the API server and SQLite storage
- `test_app.py` — integration tests
