# Book API REST Service

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint

## Requirements

- Python 3.7+
- FastAPI
- uvicorn (for running the server)

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn
```

## Running the Application

```bash
uvicorn main:app --reload
```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /books` - List all books (supports filtering by author)
- `GET /books/{id}` - Get a single book by ID
- `POST /books` - Create a new book
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Testing

Run tests with pytest:

```bash
pytest test_main.py
```

## Data Storage

The application uses SQLite for data persistence. Data is stored in a file called `books.db` in the current directory.

## Example Usage

```bash
# Create a book
curl -X POST "http://localhost:8000/books" -H "Content-Type: application/json" -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273502"}'

# Get all books
curl "http://localhost:8000/books"

# Get a specific book
curl "http://localhost:8000/books/1"

# Update a book
curl -X PUT "http://http://localhost:8000/books/1" -H "Content-Type: application/json" -d '{"title": "Updated Title", "author": "Updated Author"}'

# Delete a book
curl -X DELETE "http://localhost:8000/books/1"
```