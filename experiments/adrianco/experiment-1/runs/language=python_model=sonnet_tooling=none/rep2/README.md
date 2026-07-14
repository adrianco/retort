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

The API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

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
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

Required fields: `title`, `author`. Optional: `year`, `isbn`.

### List books

```bash
curl http://localhost:8000/books
curl http://localhost:8000/books?author=Orwell
```

## Run Tests

```bash
pytest test_api.py -v
```
