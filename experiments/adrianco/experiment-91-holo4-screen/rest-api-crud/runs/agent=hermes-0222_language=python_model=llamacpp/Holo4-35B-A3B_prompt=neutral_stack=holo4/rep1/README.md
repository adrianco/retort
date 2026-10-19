# Book Collection REST API

A Python Flask REST API for managing a book collection, backed by SQLite.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

## Setup

1. Install dependencies:
   ```bash
   pip install flask
   ```

2. Run the server:
   ```bash
   python app.py
   ```
   The server starts on http://localhost:5000

## Running Tests

```bash
python -m pytest tests/   # if pytest is available
# or
python -m unittest discover tests -v
```

## Example Requests

Create a book:
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
```

List books:
```bash
curl http://localhost:5000/books
curl "http://localhost:5000/books?author=Frank Herbert"
```
