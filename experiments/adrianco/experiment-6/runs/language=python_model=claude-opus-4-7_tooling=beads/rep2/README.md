# Books API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.10+
- `pip` for installing dependencies

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server listens on `http://0.0.0.0:5000` by default. Override the port with
`PORT=8080 python3 app.py` and the database location with
`BOOKS_DB=/path/to/books.db python3 app.py`. The SQLite schema is created
automatically on startup.

## Tests

```bash
python3 -m pytest -v
```

Tests use a temporary SQLite file per test and do not touch the production
database.

## Endpoints

| Method | Path           | Description                                   |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Health check, returns `{"status": "ok"}`      |
| POST   | `/books`       | Create a book                                 |
| GET    | `/books`       | List books, optional `?author=` filter        |
| GET    | `/books/{id}`  | Fetch a single book                           |
| PUT    | `/books/{id}`  | Update a book (partial updates supported)     |
| DELETE | `/books/{id}`  | Delete a book                                 |

### Book payload

```json
{
  "title":  "Dune",            // required, non-empty string
  "author": "Frank Herbert",   // required, non-empty string
  "year":   1965,              // optional integer
  "isbn":   "978-0441172719"   // optional string
}
```

### Examples

```bash
# Create
curl -s -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# List
curl -s http://localhost:5000/books
curl -s 'http://localhost:5000/books?author=Frank%20Herbert'

# Get one
curl -s http://localhost:5000/books/1

# Update
curl -s -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete
curl -s -X DELETE http://localhost:5000/books/1 -o /dev/null -w '%{http_code}\n'
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON or validation failure
- `404 Not Found` — unknown book id
