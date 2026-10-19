# Book Collection REST API

A small REST API for managing a book collection, built with **Python** and
**Flask**, storing data in **SQLite**.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The service listens on `http://localhost:5000`. The SQLite database is
created automatically at `books.db` in the project directory. To use a
different database file or port, set the `BOOKS_DB` / `PORT` environment
variables:

```bash
BOOKS_DB=/tmp/my_books.db PORT=8080 python app.py
```

## API Endpoints

| Method | Path             | Description                                   |
|--------|------------------|-----------------------------------------------|
| GET    | `/health`        | Health check                                  |
| POST   | `/books`         | Create a book (`title`, `author`, `year`, `isbn`) |
| GET    | `/books`         | List all books (optional `?author=` filter)   |
| GET    | `/books/{id}`    | Get a single book by ID                       |
| PUT    | `/books/{id}`    | Update a book (partial updates allowed)       |
| DELETE | `/books/{id}`    | Delete a book                                 |

### Field rules

- `title` and `author` are **required** on create; must be non-empty strings.
- `year` is optional; must be an integer when provided.
- `isbn` is optional; must be a non-empty string when provided.
- On `PUT`, any provided field is validated; `year`/`isbn` may be set to
  `null` to clear them. Unknown fields are rejected.

### Status codes

- `200` — success (list/get/update)
- `201` — book created (returns the new book with its `id`)
- `204` — book deleted
- `400` — validation error or malformed JSON body
- `404` — book or route not found
- `405` — method not allowed

All responses are JSON, including error bodies: `{"error": "..."}`.

## Examples

```bash
# Create
curl -s -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List (all / filtered)
curl -s http://localhost:5000/books
curl -s 'http://localhost:5000/books?author=Frank%20Herbert'

# Get / Update / Delete
curl -s http://localhost:5000/books/1
curl -s -X PUT http://localhost:5000/books/1 -H 'Content-Type: application/json' \
  -d '{"year": 1966}'
curl -s -X DELETE http://localhost:5000/books/1

# Health
curl -s http://localhost:5000/health
```

## Tests

The test suite (pytest) covers all endpoints: CRUD, the author filter,
validation, and error handling.

```bash
pip install pytest
pytest -v
```
