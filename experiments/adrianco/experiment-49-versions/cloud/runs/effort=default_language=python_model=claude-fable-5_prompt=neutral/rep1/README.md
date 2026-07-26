# Book Collection REST API

A small Flask service for managing a book collection, backed by SQLite.

## Requirements

- Python 3.9+
- Flask
- pytest (for tests)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
```

The server listens on `http://127.0.0.1:5000` and stores data in `books.db`
(created automatically in the working directory).

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book                                |
| GET    | `/books`      | List all books; filter with `?author=<name>` |
| GET    | `/books/{id}` | Get a single book                            |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}` | Delete a book                                |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

Validation errors return `400` with an `errors` list; missing books return `404`.

### Examples

```bash
# Create
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List (optionally filtered by author)
curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'

# Get one
curl http://127.0.0.1:5000/books/1

# Update
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -X DELETE http://127.0.0.1:5000/books/1
```

## Running the tests

```bash
pytest
```

Tests run against a temporary SQLite database per test, so they never touch
`books.db`.
