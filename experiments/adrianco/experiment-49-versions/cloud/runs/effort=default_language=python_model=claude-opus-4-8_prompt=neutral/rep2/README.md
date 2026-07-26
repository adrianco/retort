# Book Collection API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (via Python's standard-library `sqlite3` module).

## Requirements

- Python 3.8+

## Setup

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The service starts on `http://localhost:5000`. Data is persisted to a
`books.db` SQLite file in the project directory (override the location with the
`BOOKS_DB` environment variable).

## Endpoints

| Method | Path            | Description                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Health check → `{"status": "ok"}`        |
| POST   | `/books`        | Create a book                            |
| GET    | `/books`        | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`   | Get a single book                        |
| PUT    | `/books/{id}`   | Update a book                            |
| DELETE | `/books/{id}`   | Delete a book                            |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
```

List books by a given author:

```bash
curl 'http://localhost:5000/books?author=Frank%20Herbert'
```

Update a book (only supplied fields change):

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Responses & status codes

- `200 OK` — successful GET / PUT
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation error (returns `{"errors": [...]}`)
- `404 Not Found` — book does not exist

## Tests

```bash
pytest
```
