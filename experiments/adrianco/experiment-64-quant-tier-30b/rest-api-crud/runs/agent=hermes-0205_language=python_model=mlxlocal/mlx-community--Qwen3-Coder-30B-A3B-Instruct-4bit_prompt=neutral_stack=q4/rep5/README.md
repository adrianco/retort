# Book API REST Service

A REST API service for managing a book collection, built with FastAPI and SQLite.

## Features
- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage

## Requirements
- Python 3.8+
- FastAPI
- uvicorn
- sqlite3 (included in Python standard library)

## Installation

```bash
pip install fastapi uvicorn
```

## Running the Application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### Books Management
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id} - Get a single book by ID
- `POST /books` - Create a new book
- `PUT /books/{id} - Update a book by ID
- `DELETE /books/{id} - Delete a book by ID

### Example Usage

```bash
# Create a book
curl -X POST "http://localhost:8000/books" -H "Content-Type: application/json" -d '{"title": "Book Title", "author": "Author Name", "year": 2023, "isbn": "1234567890"}'

# Get all books
curl "http://localhost:8000/books"

# Get a book by ID
curl "http://localhost:8000/books/1"

# Update a book
curl -X PUT "http://http://localhost:8000/books/1" -H "Content-Type: application/json" -d '{"title": "Updated Title", "author": "Updated Author", "year": 2024, "isbn": "1234567890"}'

# Delete a book
curl -X DELETE "http://localhost:8000/books/1"
```

## Database
The application uses SQLite to store book data. All data is stored in a file called `books.db` in the working directory.