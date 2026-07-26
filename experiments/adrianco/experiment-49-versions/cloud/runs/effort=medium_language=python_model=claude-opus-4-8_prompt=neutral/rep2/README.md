# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (via Python's stdlib `sqlite3` module).

## Requirements

- Python 3.8+
- Flask (see `requirements.txt`)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on `http://localhost:5000` by default. Override with the
`PORT` environment variable, and the database location with `BOOKS_DB`
(defaults to `books.db` next to `app.py`).

```bash
PORT=8080 BOOKS_DB=/tmp/mybooks.db python3 app.py
```

## Endpoints

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`        |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List all books (optional `?author=` filter) |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book (partial update supported) |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book fields

| Field   | Type   | Required | Notes                     |
|---------|--------|----------|---------------------------|
| title   | string | yes      | non-empty                 |
| author  | string | yes      | non-empty                 |
| year    | int    | no       |                           |
| isbn    | string | no       |                           |

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}'

# List (filter by author)
curl http://localhost:5000/books?author=Donovan

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":2016}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error (returns `{"errors": [...]}`)
- `404 Not Found` — book does not exist

## Tests

```bash
python3 -m pytest -q
```

13 integration tests cover the health check, CRUD operations, the author
filter, validation rules, and 404 handling.
