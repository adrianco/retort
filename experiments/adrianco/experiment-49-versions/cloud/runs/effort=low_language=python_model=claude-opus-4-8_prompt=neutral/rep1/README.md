# Book Collection API

A small REST API service for managing a book collection, built with **Flask** and **SQLite**.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

The server starts on `http://localhost:5000` (override with the `PORT` env var).
Data is stored in a SQLite file `books.db` (override with the `BOOKS_DB` env var).
The database schema is created automatically on startup.

## Run the tests

```bash
python3 -m pytest
```

## API

All responses are JSON. Books have the shape:

```json
{ "id": 1, "title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0261102217" }
```

`title` and `author` are required and must be non-empty strings. `year` (integer)
and `isbn` (string) are optional.

| Method | Path            | Description                              | Success |
|--------|-----------------|------------------------------------------|---------|
| GET    | `/health`       | Health check                             | 200     |
| POST   | `/books`        | Create a book                            | 201     |
| GET    | `/books`        | List books; optional `?author=` filter   | 200     |
| GET    | `/books/{id}`   | Get one book                             | 200     |
| PUT    | `/books/{id}`   | Update a book (partial updates allowed)  | 200     |
| DELETE | `/books/{id}`   | Delete a book                            | 204     |

Errors return an appropriate status code (`400` invalid input, `404` not found)
with a JSON body `{ "error": "..." }`.

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0261102217"}'

# List / filter
curl http://localhost:5000/books
curl 'http://localhost:5000/books?author=J.R.R.%20Tolkien'

# Get / update / delete
curl http://localhost:5000/books/1
curl -X PUT http://localhost:5000/books/1 -H 'Content-Type: application/json' -d '{"year":1954}'
curl -X DELETE http://localhost:5000/books/1
```
