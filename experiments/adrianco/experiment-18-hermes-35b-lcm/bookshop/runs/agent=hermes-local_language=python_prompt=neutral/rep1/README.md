# Book Collection REST API

A simple REST API for managing a collection of books, built with **FastAPI** and **SQLite**.

## Endpoints

| Method   | Path             | Description                        |
|----------|------------------|------------------------------------|
| GET      | /health          | Health check                       |
| POST     | /books           | Create a new book                  |
| GET      | /books           | List all books (filter by `?author=`) |
| GET      | /books/{id}      | Get a single book by ID            |
| PUT      | /books/{id}      | Update a book                      |
| DELETE   | /books/{id}      | Delete a book                      |

## Prerequisites

- Python 3.11+
- pip

## Setup

1. **Install dependencies** (if not already present):

```bash
pip install fastapi uvicorn pydantic pytest httpx
```

2. **Run the server**:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

Swagger docs: `http://localhost:8000/docs`

## Testing

Run the test suite with:

```bash
pytest tests/ -v
```

## Example: Create a book

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'
```

## Example: List books filtered by author

```bash
curl http://localhost:8000/books?author=George+Orwell
```

## Configuration

Set the `BOOK_DB` environment variable to change the SQLite database file location. Default: `books.db`.

```bash
BOOK_DB=/tmp/books.db uvicorn app:app --port 8000
```
