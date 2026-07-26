# Books REST API

A minimal REST API for managing a book collection, built with Flask and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server listens on `http://localhost:5000`. Data is persisted to `books.db`
in the working directory (override with the `BOOKS_DB` environment variable).

## Endpoints

| Method | Path              | Description                              |
| ------ | ----------------- | ---------------------------------------- |
| GET    | `/health`         | Health check → `{"status": "ok"}`        |
| POST   | `/books`          | Create a book (`title`, `author` required; `year`, `isbn` optional) |
| GET    | `/books`          | List all books; optional `?author=` filter |
| GET    | `/books/{id}`     | Fetch a book by ID                       |
| PUT    | `/books/{id}`     | Update a book (partial fields allowed)   |
| DELETE | `/books/{id}`     | Delete a book                            |

### Example

```bash
curl -X POST http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:5000/books?author=Frank%20Herbert
```

## Tests

```bash
python -m pytest -v
```
