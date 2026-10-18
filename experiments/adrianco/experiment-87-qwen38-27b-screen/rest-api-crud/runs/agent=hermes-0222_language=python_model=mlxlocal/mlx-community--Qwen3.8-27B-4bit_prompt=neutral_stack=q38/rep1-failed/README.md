# Book Collection REST API

A small REST API service for managing a book collection, built with
[Flask](https://flask.palletsprojects.com/) and backed by SQLite.

## Features

- Full CRUD for books: `title`, `author`, `year`, `isbn`
- List all books, with optional `?author=` filter
- Input validation — `title` and `author` are required non-empty strings;
  `year` (optional) must be an integer; `isbn` (optional) must be a string
- JSON responses with appropriate HTTP status codes on every endpoint,
  including 404/405 error paths
- Health check endpoint

## Setup

Python 3.9+ is required.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The API listens on `http://localhost:5000`. Override the port with the
`PORT` environment variable, or the database location with `BOOKS_DB`
(default: `books.db` in the current directory).

## API

| Method | Path             | Description                                  | Success |
|--------|------------------|----------------------------------------------|---------|
| GET    | `/health`        | Health check                                 | 200     |
| POST   | `/books`         | Create a book                                | 201     |
| GET    | `/books`         | List books (optional `?author=` filter)      | 200     |
| GET    | `/books/{id}`    | Get one book                                 | 200     |
| PUT    | `/books/{id}`    | Update a book (full replace)                 | 200     |
| DELETE | `/books/{id}`    | Delete a book                                | 200     |

Errors return `400` (validation / bad JSON), `404` (unknown book or route),
or `405` (wrong method), always as JSON.

### Examples

```bash
# Health
curl http://localhost:5000/health

# Create
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-261-10235-9"}'

# List
curl http://localhost:5000/books

# List by author
curl 'http://localhost:5000/books?author=J.R.R.%20Tolkien'

# Get one
curl http://localhost:5000/books/1

# Update
curl -X PUT http://localhost:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit (Revised)", "author": "J.R.R. Tolkien", "year": 1951}'

# Delete
curl -X DELETE http://localhost:5000/books/1
```

## Tests

```bash
python -m pytest test_app.py -v
```

The test suite (in `test_app.py`) covers the health check, all CRUD
operations, the author filter, validation failures (missing/empty
`title`/`author`, bad `year`, malformed JSON), and 404/405 error paths.
Each test uses a throwaway SQLite database in a temp directory, so runs
are isolated and repeatable.

## Project layout

```
app.py            Flask application (factory pattern, all routes)
test_app.py       pytest test suite
requirements.txt  Python dependencies
books.db          SQLite database (created at runtime)
```
