# Book API REST Service

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create books with title, author, year, and ISBN
- List all books (with optional author filter)
- Get a single book by ID
- Update book information
- Delete books
- Health check endpoint
- Input validation (title and author are required)

## Requirements

- Python 3.8+
- SQLite (included with Python standard library)

## Installation

1. Clone or copy the project files to your working directory

2. Install dependencies:
```bash
pip install fastapi uvicorn
```

## Running the Application

### Start the server:
```bash
python main.py
```

Or use uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /books | List all books |
| GET | /books?author={name} | Filter books by author |
| GET | /books/{id} | Get a single book |
| POST | /books | Create a new book |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Example Usage

#### Create a book:
```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

#### List all books:
```bash
curl http://localhost:8000/books
```

#### Get a book by ID:
```bash
curl http://localhost:8000/books/1
```

#### Update a book:
```bash
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

#### Delete a book:
```bash
curl -X DELETE http://localhost:8000/books/1
```

## Running Tests

Run the test suite with pytest:
```bash
pytest tests/
```

Or with verbose output:
```bash
pytest tests/ -v
```

## Project Structure

```
.
├── main.py          # FastAPI application with all endpoints
├── database.py      # SQLite database operations
├── models.py        # Pydantic data models
├── tests/
│   ├── __init__.py
│   └── test_api.py  # API tests
├── README.md        # This file
└── books.db         # SQLite database (created at runtime)
```

## Notes

- The database file is `books.db` by default
- Set `DATABASE_PATH` environment variable to use a different database location
- For testing, the database is `test_books.db`
