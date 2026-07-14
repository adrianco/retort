# Books REST API

A simple Flask + SQLite REST API for managing a collection of books.

## Requirements

- Python 3.9+
- Dependencies in `requirements.txt` (Flask, pytest)

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

The server listens on `http://localhost:5000` by default. Override with
`PORT=8080 python3 app.py`. The SQLite file path can be overridden with
`BOOKS_DB=/path/to/books.db`.

## Run tests

```bash
python3 -m pytest -q
```

## Endpoints

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check — returns `{"status":"ok"}` |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books (supports `?author=` filter)  |
| GET    | `/books/{id}`  | Get a single book                        |
| PUT    | `/books/{id}`  | Update a book (partial updates allowed)  |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required (non-empty strings). `year` (integer) and
`isbn` (string) are optional.

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List, filtered by author
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failed
- `404 Not Found` — book id does not exist
