# Book API REST Service

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Requirements

- Python 3.7+
- FastAPI
- uvicorn

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /books` - List all books (supports filtering by author)
- `GET /books/{id}` - Get a single book by ID
- `POST /books` - Create a new book
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Example Usage

### Create a book
```bash
curl -X POST "http://localhost:8000/books" \
     -H "Content-Type: application/json" \
     -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925}'
```

### Get all books
```bash
curl "http://localhost:8000/books"
```

### Get a specific book
```bash
curl "http://localhost:8000/books/1"
```

### Update a book
```bash
curl -X PUT "http://localhost:8000/books/1" \
     -H "Content-Type: application/json" \
     -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925}'
```

### Delete a book
```bash
curl -X DELETE "http://localhost:8000/books/1"
```

## Testing

Run tests with:

```bash
python -m pytest tests.py -v
```

## Testing

Run tests with:

```bash
python -m pytest tests.py -v
```