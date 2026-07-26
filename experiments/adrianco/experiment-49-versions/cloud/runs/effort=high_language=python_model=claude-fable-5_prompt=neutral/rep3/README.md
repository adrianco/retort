# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask
- pytest (for tests)

Install dependencies:

```sh
pip install -r requirements.txt
```

## Running the server

```sh
python app.py
```

The server listens on `http://127.0.0.1:8000` (port 5000 is often taken by
AirPlay Receiver on macOS; set the `PORT` environment variable to change it).
Data is stored in `books.db` in the current directory; set the `BOOKS_DB`
environment variable to use a different path.

## API

| Method | Path          | Description                                    |
|--------|---------------|------------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`      |
| POST   | `/books`      | Create a book (JSON body)                      |
| GET    | `/books`      | List all books; filter with `?author=<name>`   |
| GET    | `/books/{id}` | Get a single book                              |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)        |
| DELETE | `/books/{id}` | Delete a book                                  |

Book fields: `title` (string, required), `author` (string, required),
`year` (integer, optional), `isbn` (string, optional).

Status codes: `201` on create, `200` on reads/updates, `204` on delete,
`400` for validation errors (body includes an `errors` list), `404` when a
book does not exist.

### Examples

```sh
# Create
curl -s -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

# List / filter
curl -s http://127.0.0.1:8000/books
curl -s 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Get one
curl -s http://127.0.0.1:8000/books/1

# Update
curl -s -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -s -X DELETE http://127.0.0.1:8000/books/1 -i
```

## Running the tests

```sh
pytest
```

Tests run against a temporary database, so they never touch `books.db`.
