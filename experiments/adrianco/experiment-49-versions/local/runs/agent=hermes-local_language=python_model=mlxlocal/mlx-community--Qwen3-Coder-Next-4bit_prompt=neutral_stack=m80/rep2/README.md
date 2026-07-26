# Book API REST Service

A REST API service for managing a book collection using Python, Flask, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports ?author= filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Python 3.7+
- Flask
- pytest (for testing)

## Installation

1. Clone or copy the project files to your working directory

2. Install dependencies:
```bash
pip install flask pytest
```

Or if using pip3:
```bash
pip3 install flask pytest
```

## Usage

### Running the Server

```bash
python app.py
```

Or with Python 3:
```bash
python3 app.py
```

The server will start on `http://0.0.0.0:5000`

### API Endpoints

#### Health Check
```bash
curl http://localhost:5000/health
```

#### Create a Book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

#### Get All Books
```bash
curl http://localhost:5000/books
```

#### Get All Books by Author
```bash
curl "http://localhost:5000/books?author=George%20Orwell"
```

#### Get a Single Book
```bash
curl http://localhost:5000/books/1
```

#### Update a Book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated Edition)"}'
```

#### Delete a Book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

Run the test suite:
```bash
pytest test_app.py -v
```

Or with Python 3:
```bash
python3 -m pytest test_app.py -v
```

## Project Structure

- `app.py` - Main Flask application with all API endpoints
- `test_app.py` - Unit and integration tests
- `books.db` - SQLite database (created automatically)
- `README.md` - This file

## Error Handling

The API returns appropriate HTTP status codes:
- 200 - Success
- 201 - Created
- 400 - Bad Request (validation errors)
- 404 - Not Found
- 500 - Internal Server Error

Validation errors return a JSON response with the list of errors.
