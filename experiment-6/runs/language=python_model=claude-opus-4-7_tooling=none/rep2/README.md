# Books REST API

A small REST API for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.9+
- See `requirements.txt`

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

The server listens on `http://0.0.0.0:5000` by default. Override with the
`PORT` environment variable, and the SQLite database location with `BOOKS_DB`
(defaults to `books.db` in the working directory).

## Tests

```bash
pytest -v
```

## Endpoints

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Health check, returns `{"status": "ok"}`     |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List books (optional `?author=` filter)      |
| GET    | `/books/{id}`  | Fetch a single book                          |
| PUT    | `/books/{id}`  | Update a book (any subset of fields)         |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book schema

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0345339683"
}
```

`title` and `author` are required on create. `year` (if provided) must be an
integer; `isbn` (if provided) must be a string.

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl http://localhost:5000/books?author=Frank%20Herbert
```

## Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid or missing JSON, failed validation
- `404 Not Found` — book id does not exist
