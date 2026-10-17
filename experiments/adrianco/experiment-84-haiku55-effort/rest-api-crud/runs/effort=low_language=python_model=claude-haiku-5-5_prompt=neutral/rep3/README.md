# Books API

A small REST API for managing a book collection. Built with the Python standard
library (`http.server` and `sqlite3`), so there are no third-party runtime
dependencies. Data is stored in a SQLite file.

## Requirements

- Python 3.10 or newer

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest   # only needed to run the tests
```

## Run

```bash
python books_api.py                       # http://127.0.0.1:8000, database ./books.db
python books_api.py --port 9000 --db /tmp/books.db
```

## Test

```bash
python -m pytest -q
```

## Data model

| Field    | Type    | Required | Notes                              |
|----------|---------|----------|------------------------------------|
| `id`     | integer | —        | Assigned by the server             |
| `title`  | string  | yes      | Non-empty after trimming           |
| `author` | string  | yes      | Non-empty after trimming           |
| `year`   | integer | no       | 0 to 9999                          |
| `isbn`   | string  | no       | Non-empty when given; must be unique |

## Endpoints

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                | 201 + body, `Location` header |
| GET    | `/books`      | List books; optional `?author=` filter       | 200     |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book (`title` and `author` required; omitted `year`/`isbn` are cleared) | 200 |
| DELETE | `/books/{id}` | Delete a book                                | 204     |
| GET    | `/health`     | Health check                                 | 200     |

The `?author=` filter matches the full author name, ignoring case
(`?author=frank herbert` matches `Frank Herbert`).

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

# List, filtered by author
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Get one
curl http://127.0.0.1:8000/books/1

# Update
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# Delete
curl -i -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Error responses

Errors return a JSON body of the form `{"error": "..."}`. Validation failures
also include `"details"`, a list of messages.

| Status | When                                                         |
|--------|--------------------------------------------------------------|
| 400    | Invalid JSON, missing or invalid fields, or missing body     |
| 404    | Unknown route, non-numeric ID, or book not found             |
| 409    | ISBN already used by another book                            |
| 500    | Unexpected server error                                      |

## Files

- `books_api.py`: server, routing, validation, and SQLite storage
- `test_books_api.py`: integration tests that run the real server on an ephemeral port
