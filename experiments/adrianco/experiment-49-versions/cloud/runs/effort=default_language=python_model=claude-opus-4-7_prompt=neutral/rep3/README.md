# Book Collection REST API

A minimal REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask
- pytest (for tests)

## Setup

```bash
pip install -r requirements.txt
```

## Running the service

```bash
python app.py
```

The service listens on `http://0.0.0.0:5000` by default. Override the port with
the `PORT` environment variable, and the SQLite file location with `BOOKS_DB`:

```bash
PORT=8080 BOOKS_DB=/tmp/books.db python app.py
```

## Endpoints

| Method | Path            | Description                                   |
| ------ | --------------- | --------------------------------------------- |
| GET    | `/health`       | Health check, returns `{"status": "ok"}`      |
| POST   | `/books`        | Create a book                                 |
| GET    | `/books`        | List books; supports `?author=` filter        |
| GET    | `/books/{id}`   | Get a book by ID                              |
| PUT    | `/books/{id}`   | Update a book                                 |
| DELETE | `/books/{id}`   | Delete a book                                 |

### Book payload

```json
{
  "title":  "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year":   1937,
  "isbn":   "978-0261102217"
}
```

- `title` and `author` are required non-empty strings.
- `year` is an optional integer.
- `isbn` is an optional string.

### Example

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# List all
curl http://localhost:5000/books

# Filter by author
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (missing/invalid fields)
- `404 Not Found` — no book with the given ID

## Tests

```bash
pytest -v
```
