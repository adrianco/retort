# Book Collection REST API

A small REST API for managing a book collection, built with **Flask** and
**SQLite** (Python stdlib `sqlite3`).

## Endpoints

| Method | Path             | Description                                        | Success | Errors |
|--------|------------------|----------------------------------------------------|---------|--------|
| GET    | `/health`        | Health check                                       | 200     |        |
| POST   | `/books`         | Create a book (`title`, `author` required; `year`, `isbn` optional) | 201 | 400 |
| GET    | `/books`         | List all books; optional `?author=` filter         | 200     |        |
| GET    | `/books/{id}`    | Get a single book by ID                            | 200     | 404 |
| PUT    | `/books/{id}`    | Update a book (partial updates; `year: null` clears it) | 200 | 400, 404 |
| DELETE | `/books/{id}`    | Delete a book                                      | 200     | 404 |

Book JSON shape:

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0547928227"
}
```

## Setup

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
# or: flask --app app run
```

The server listens on `http://0.0.0.0:5000`. Data is stored in `books.db`
in the working directory (override with the `BOOKS_DB` environment variable).

Note: on macOS, port 5000 is often taken by the AirPlay Receiver. If you get
"Address already in use", run it on another port, e.g.:

```bash
python -c "from app import app; app.run(host='0.0.0.0', port=8000)"
```

### Example requests

```bash
curl http://localhost:5000/health

curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'

curl 'http://localhost:5000/books?author=Tolkien'
curl http://localhost:5000/books/1
curl -X PUT http://localhost:5000/books/1 -H 'Content-Type: application/json' -d '{"year": 1938}'
curl -X DELETE http://localhost:5000/books/1
```

## Validation rules

- `title` and `author` are required, non-empty strings (400 otherwise).
- `year` must be an integer (or a digit string); `null` clears it on update.
- `isbn` must be a string when provided.
- Non-JSON or malformed request bodies return 400.
- Unknown book IDs return 404 with `{"error": "Book not found"}`.

## Tests

```bash
pytest -q
```

22 integration tests cover the health check, CRUD operations, the author
filter, validation errors, and 404 handling.
