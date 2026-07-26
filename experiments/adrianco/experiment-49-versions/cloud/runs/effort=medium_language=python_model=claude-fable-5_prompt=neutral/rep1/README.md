# Book Collection API

A REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- Flask, pytest

```bash
pip install -r requirements.txt
```

## Running the server

```bash
python app.py
```

The server starts on `http://127.0.0.1:5000` and stores data in `books.db`
(override the path with the `BOOKS_DATABASE` environment variable).

## Endpoints

| Method | Path          | Description                                    |
|--------|---------------|------------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status": "ok"}`      |
| POST   | `/books`      | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`      | List all books; filter with `?author=<name>`   |
| GET    | `/books/{id}` | Get a single book                              |
| PUT    | `/books/{id}` | Update a book (partial updates supported)      |
| DELETE | `/books/{id}` | Delete a book                                  |

Validation errors return `400` with an `errors` list; missing books return `404`.

### Example

```bash
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'

curl 'http://127.0.0.1:5000/books?author=Frank%20Herbert'
```

## Tests

```bash
python -m pytest -v
```
