# Book API Service

A REST API service for managing a book collection with SQLite backend.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Endpoints

### Health Check
- `GET /health` - Check service health

### Books
- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `author` query param)
- `GET /books/:id` - Get a single book by ID
- `PUT /books/:id` - Update a book
- `DELETE /books/:id` - Delete a book

## Requirements

- Node.js (v14 or higher)
- npm

## Setup

1. Install dependencies:
```bash
npm install
```

2. Build the project:
```bash
npm run build
```

3. Start the server:
```bash
npm start
```

## Testing

Run the tests:
```bash
npm test
```

## API Usage Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Filter books by author
```bash
curl http://localhost:3000/books?author=Fitzgerald
```

### Get a book by ID
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Updated",
    "author": "F. Scott Fitzgerald",
    "year": 1925
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

## Implementation Details

This implementation uses a SQLite database to persist book data. The server is built with Express.js and TypeScript.

The API supports all required operations:
- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

Input validation ensures title and author are required fields.