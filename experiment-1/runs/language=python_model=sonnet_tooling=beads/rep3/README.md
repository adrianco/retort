# Book Collection API

A REST API for managing a book collection, built with FastAPI and SQLite.

## Setup

```bash
pip install fastapi uvicorn sqlalchemy pytest httpx
```

## Run

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a new book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Create a book

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
```

`title` and `author` are required. `year` and `isbn` are optional.

### List books

```bash
curl http://localhost:8000/books
curl "http://localhost:8000/books?author=Frank+Herbert"
```

## Run Tests

```bash
pytest test_books.py -v
```
