# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database for persistent storage
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. The API will be available at `http://localhost:5001`

## Testing

Run the tests with:
```
python -m pytest test_app.py -v
```

## Requirements

- Python 3.6+
- Flask
- SQLite (included with Python)