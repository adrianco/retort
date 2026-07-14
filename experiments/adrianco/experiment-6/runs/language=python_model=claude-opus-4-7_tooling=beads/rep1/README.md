# Books REST API

A small Flask REST API for managing a book collection, backed by SQLite.

## Requirements

- Python 3.10+
- Flask, pytest (see `requirements.txt`)

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

The server listens on `http://0.0.0.0:5000` by default. Override with the `PORT`
environment variable. Override the SQLite file path with `DATABASE`.

```bash
PORT=8080 DATABASE=/tmp/books.db python3 app.py
```

## Test

```bash
python3 -m pytest tests/ -v
```

## Endpoints

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check — returns `{"status":"ok"}` |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`  | Get a book by id                         |
| PUT    | `/books/{id}`  | Update a book (partial update allowed)   |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

- `title` (string, required, non-empty)
- `author` (string, required, non-empty)
- `year` (integer, optional)
- `isbn` (string, optional)

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List
curl http://localhost:5000/books
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Get
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

## Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation error
- `404 Not Found` — book or route does not exist
- `405 Method Not Allowed` — wrong HTTP verb for a route
