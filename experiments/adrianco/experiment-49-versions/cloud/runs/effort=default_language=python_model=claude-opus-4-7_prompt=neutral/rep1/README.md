# Books REST API

A minimal REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- pip

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the server

```bash
python app.py
```

The server listens on `http://0.0.0.0:5000` by default. Override with the
`PORT` environment variable. The SQLite database file location can be set
with `BOOKS_DB` (defaults to `books.db` in the working directory).

## Endpoints

| Method | Path             | Description                                |
| ------ | ---------------- | ------------------------------------------ |
| GET    | `/health`        | Health check — returns `{"status": "ok"}`  |
| POST   | `/books`         | Create a new book                          |
| GET    | `/books`         | List all books (optional `?author=` filter) |
| GET    | `/books/{id}`    | Get a book by ID                           |
| PUT    | `/books/{id}`    | Update a book                              |
| DELETE | `/books/{id}`    | Delete a book                              |

### Book schema

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0345339683"
}
```

`title` and `author` are required non-empty strings. `year` (integer) and
`isbn` (string) are optional.

### Example

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# List, filtered
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

## Response codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure or malformed JSON
- `404 Not Found` — book (or route) does not exist

## Tests

```bash
pytest
```
