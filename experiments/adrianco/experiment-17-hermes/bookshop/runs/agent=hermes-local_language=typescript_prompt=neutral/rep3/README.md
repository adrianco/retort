# Book Collection REST API

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database for data persistence

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Setup

1. Install dependencies:
   ```
   npm install
   ```

2. Build the project:
   ```
   npm run build
   ```

3. Start the server:
   ```
   npm start
   ```

## Running Tests

```
npm test
```

## Example Usage

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

### Get all books
```bash
curl http://localhost:3000/books
```

### Get books by author
```bash
curl "http://localhost:3000/books?author=Fitzgerald"
```

### Get a single book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Revised Edition",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```
