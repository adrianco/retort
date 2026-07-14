# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update an existing book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Details

- **Framework**: Flask (Python)
- **Database**: SQLite (embedded, no external server needed)
- **Response Format**: JSON with appropriate HTTP status codes
- **Validation**: Title and author are required fields

## Setup and Run Instructions

### 1. Install Dependencies

```bash
pip install flask pytest
```

### 2. Run the Application

```bash
python app.py
```

The API will be available at `http://localhost:5000`

### 3. Run Tests

```bash
pytest test_app.py -v
```

## API Usage Examples

### Create a Book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List All Books

```bash
curl http://localhost:5000/books
```

### List Books by Author

```bash
curl "http://localhost:5000/books?author=Orwell"
```

### Get a Single Book

```bash
curl http://localhost:5000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health Check

```bash
curl http://localhost:5000/health
```

## Project Structure

- `app.py` - Main application with all API endpoints
- `test_app.py` - Comprehensive acceptance tests (20+ test cases)
- `README.md` - This file
- `requirements.txt` - Python dependencies
