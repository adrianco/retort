# Book Collection REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask, pytest (see `requirements.txt`)

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```sh
python3 app.py
```

The server listens on `http://127.0.0.1:5001` (5001 rather than 5000 because
macOS AirPlay Receiver commonly occupies 5000) and stores data in `books.db`
(created automatically in the working directory). To use a different port or
database, call `create_app()` yourself:

```sh
python3 -c "from app import create_app; create_app('books.db').run(port=8080)"
```

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`    |
| POST   | `/books`      | Create a book                                |
| GET    | `/books`      | List books; optional `?author=` exact filter (case-insensitive) |
| GET    | `/books/{id}` | Get one book                                 |
| PUT    | `/books/{id}` | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}` | Delete a book                                |

A book has the fields `title` (string, required), `author` (string, required),
`year` (integer, optional), and `isbn` (string, optional).

### Status codes

- `200` — successful read/update
- `201` — book created
- `204` — book deleted
- `400` — validation error (details in an `errors` array)
- `404` — book not found

### Examples

```sh
# Create
curl -X POST http://127.0.0.1:5001/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List, filtered by author
curl 'http://127.0.0.1:5001/books?author=Frank%20Herbert'

# Get / update / delete
curl http://127.0.0.1:5001/books/1
curl -X PUT http://127.0.0.1:5001/books/1 -H 'Content-Type: application/json' -d '{"year": 1966}'
curl -X DELETE http://127.0.0.1:5001/books/1
```

## Tests

```sh
python3 -m pytest -v
```

Tests run against a temporary database, so they never touch `books.db`.
