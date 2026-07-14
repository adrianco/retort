# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create books with title, author, year, and ISBN
- List all books with optional author filtering
- Get, update, and delete individual books
- Input validation (title and author are required)
- SQLite database for persistent storage
- Health check endpoint

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

| Method | Endpoint          | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | /health           | Health check endpoint                |
| POST   | /books            | Create a new book                    |
| GET    | /books            | List all books (supports ?author=)   |
| GET    | /books/{id}       | Get a single book by ID              |
| PUT    | /books/{id}       | Update a book                        |
| DELETE | /books/{id}       | Delete a book                        |

### Request/Response Examples

**Create a book:**
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

**List all books:**
```bash
curl http://localhost:5000/books
```

**List books by author:**
```bash
curl "http://localhost:5000/books?author=Orwell"
```

**Get a book by ID:**
```bash
curl http://localhost:5000/books/1
```

**Update a book:**
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four"}'
```

**Delete a book:**
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

Run the test suite with pytest:

```bash
pytest test_app.py -v
```

## Validation Rules

- `title` is required and must be a non-empty string
- `author` is required and must be a non-empty string
- `year` (if provided) must be a valid integer
- `isbn` is optional but must be unique across all books
