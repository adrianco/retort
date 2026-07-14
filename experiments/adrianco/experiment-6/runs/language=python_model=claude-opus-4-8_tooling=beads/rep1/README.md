# Book Collection API

A small REST API for managing a collection of books, built with **Flask** and
backed by **SQLite**.

## Requirements

- Python 3.9+
- Flask (`pip install flask`)

## Setup

```bash
# (optional) create a virtual environment
python3 -m venv venv
source venv/bin/activate

pip install flask
```

## Run

```bash
python app.py
```

The service starts on `http://localhost:5000` and creates a `books.db` SQLite
file in the project directory on first run.

## Endpoints

| Method | Path           | Description                                   |
|--------|----------------|-----------------------------------------------|
| GET    | `/health`      | Health check — returns `{"status": "ok"}`     |
| POST   | `/books`       | Create a book                                 |
| GET    | `/books`       | List books (optional `?author=` filter)       |
| GET    | `/books/{id}`  | Fetch a single book                           |
| PUT    | `/books/{id}`  | Update a book (partial updates allowed)       |
| DELETE | `/books/{id}`  | Delete a book                                 |

### Book fields

| Field    | Type    | Required | Notes                  |
|----------|---------|----------|------------------------|
| `title`  | string  | yes      | Non-empty              |
| `author` | string  | yes      | Non-empty              |
| `year`   | integer | no       | Publication year       |
| `isbn`   | string  | no       |                        |

`title` and `author` are required when creating a book. Unknown fields in the
request body are ignored.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure (response includes an `errors` list)
- `404 Not Found` — no book with the given id

## Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all
curl http://localhost:5000/books

# Filter by author
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

## Tests

The test-suite uses Flask's test client against a temporary SQLite database, so
each run is isolated. Run with either runner:

```bash
python -m unittest -v
# or, if pytest is installed:
python -m pytest -v
```
