# Book Collection API

A REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Create a book

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "isbn": "9780132350884"}'
```

`title` and `author` are required. `year` and `isbn` are optional.

### List books

```bash
curl http://localhost:8000/books
curl "http://localhost:8000/books?author=Martin"
```

## Tests

```bash
pytest test_books.py -v
```

## Configuration

Set the `DB_PATH` environment variable to change the SQLite database location (defaults to `books.db`).
