# Book API REST Service

A REST API service for managing a book collection with SQLite database.

## Features

- REST API endpoints for managing books
- SQLite database storage
- Full CRUD functionality (Create, Read, Update, Delete)
- Input validation
- JSON responses with proper HTTP status codes

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### Book Management
- `POST /books` - Create a new book
- `GET /books` - List all books (with optional author filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Implementation Details

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
```

### Implementation Requirements
- All CRUD operations implemented
- REST API with proper HTTP status codes
- JSON responses
- SQLite database with all fields stored
- Input validation (title and author required)
- Health check endpoint

## Testing

### Unit Tests
The following tests can be implemented to test:

1. **Health Check Endpoint**: Verify health check returns healthy status
2. **Create Book**: Test creating a new book with valid data
3. **Get Book by ID**: Test fetching a single book by ID
4. **Update Book**: Test updating book details
5. **Delete Book**: Test deleting a book by ID
6. **List Books**: Test listing all books
7. **Filter by Author**: Test filtering books by author name

## Setup Instructions

1. Install required packages:
   ```bash
   pip install flask sqlite3
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. The API will be available at http://localhost:5000

## Example Usage

```bash
# Create a new book
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273502"}'

# Get all books
curl http://localhost:5000/books

# Get a book by ID
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273502"}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```

## Implementation Details

### Data Storage
All book data is stored in an SQLite database file (`books.db`) with the following schema:

```sql
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
```

### Error Handling
- Returns appropriate HTTP status codes (200, 201, 400, 404, 500)
- Proper error messages in JSON format for error responses
- Database errors handled gracefully

### Implementation Requirements
- All CRUD operations implemented
- Input validation (title and author required)
- Health check endpoint
- SQLite database storage
- JSON responses with proper HTTP status codes

## Testing

### Unit Tests
Unit tests should verify:

1. Health check returns healthy status
2. Creating books with valid data works
3. Getting books by ID works
4. Updating books works
5. Deleting books works
6. Filter by author works
7. Error handling works (404 for non-existent books, 400 for invalid data)
8. List all books works

### Integration Tests
Integration tests should test:
- Full CRUD cycle for books
- Error handling for invalid requests
- Database persistence between API calls