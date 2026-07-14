# Book API REST Service

A simple REST API for managing a book collection with SQLite storage.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Requirements

- Python 3.7+
- Flask
- SQLite (built-in)

## Setup

1. Install dependencies:
   ```bash
   pip install flask
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## API Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Testing

Run tests with:
```bash
python -m pytest tests.py
```
