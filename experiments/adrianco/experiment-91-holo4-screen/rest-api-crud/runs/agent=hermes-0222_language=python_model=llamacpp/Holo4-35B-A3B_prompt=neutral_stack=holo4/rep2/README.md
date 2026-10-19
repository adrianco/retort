# Book Collection REST API

A REST API service for managing a book collection, built with Python, Flask, and SQLite.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (optional `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

### Create a Book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List Books

```bash
curl http://localhost:5000/books
curl "http://localhost:5000/books?author=F. Scott Fitzgerald"
```

### Get a Book

```bash
curl http://localhost:5000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Setup

1. Install dependencies:
   ```bash
   pip install flask
   ```

2. Run the server:
   ```bash
   python app.py
   ```

   The server will start on `http://localhost:5000`.

## Running Tests

```bash
python test_app.py
```
