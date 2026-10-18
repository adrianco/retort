# Book Collection REST API

A REST API service for managing a book collection, built with Python (Flask) and SQLite.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt` (Flask; pytest for tests)

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The API listens on `http://localhost:5000` (override with the `PORT`
environment variable). The SQLite database file
(`books.db` by default) is created automatically on first run. To use a
different database location, set the `BOOKS_DB` environment variable:

```bash
BOOKS_DB=/path/to/my_books.db PORT=8080 python app.py
```

## API Endpoints

| Method | Path            | Description                          | Success |
|--------|-----------------|--------------------------------------|---------|
| GET    | `/health`       | Health check                         | 200     |
| POST   | `/books`        | Create a book                        | 201     |
| GET    | `/books`        | List all books (`?author=` filter)   | 200     |
| GET    | `/books/<id>`   | Get a single book                    | 200     |
| PUT    | `/books/<id>`   | Update a book (partial updates OK)   | 200     |
| DELETE | `/books/<id>`   | Delete a book                        | 204     |

### Book fields

- `title` (string, **required**)
- `author` (string, **required**)
- `year` (integer, optional)
- `isbn` (string, optional)

### Examples

```bash
# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

# List (all)
curl http://localhost:5000/books

# List filtered by author
curl 'http://localhost:5000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1966}'

# Delete
curl -X DELETE http://localhost:5000/books/1

# Health
curl http://localhost:5000/health
```

### Error responses

All errors return a JSON body of the form `{"error": "<message>"}`:

- `400` — missing/invalid input (e.g. `title` or `author` missing or empty,
  non-integer `year`, non-JSON body)
- `404` — book with the given ID does not exist

## Tests

Run the test suite (18 tests covering all endpoints, validation, filtering,
and error cases):

```bash
python -m pytest test_app.py -v
```
