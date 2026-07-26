# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite**.

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt` (Flask, pytest)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on `http://localhost:5000` and creates a `books.db`
SQLite file in the working directory on first run.

## API

| Method | Path             | Description                                  |
|--------|------------------|----------------------------------------------|
| GET    | `/health`        | Health check → `{"status": "ok"}`            |
| POST   | `/books`         | Create a book                                |
| GET    | `/books`         | List books (optional `?author=` filter)      |
| GET    | `/books/{id}`    | Get a single book                            |
| PUT    | `/books/{id}`    | Update a book (partial updates allowed)      |
| DELETE | `/books/{id}`    | Delete a book                                |

### Book fields

| Field    | Type    | Required | Notes                     |
|----------|---------|----------|---------------------------|
| `title`  | string  | yes      | non-empty                 |
| `author` | string  | yes      | non-empty                 |
| `year`   | integer | no       |                           |
| `isbn`   | string  | no       |                           |

### Example

```bash
# Create a book
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}'

# List books by author
curl 'http://localhost:5000/books?author=Alan%20Donovan'

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 2016}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```

### Status codes

- `200` — successful GET/PUT
- `201` — book created
- `204` — book deleted
- `400` — validation error (missing/empty `title` or `author`, bad types)
- `404` — book not found

## Tests

```bash
pytest -v
```
