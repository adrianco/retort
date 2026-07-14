# Book API

A REST API service for managing a book collection.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the server:
   ```bash
   npm start
   ```

## Testing

The API can be tested manually with curl or any HTTP client:

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Get a book by ID
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":1926}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```
