# Book API REST Service

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/:id** - Get a single book by ID
- **PUT /books/:id** - Update a book
- **DELETE /books/:id** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Node.js >= 16
- npm

## Setup and Run

1. Install dependencies:
   ```
   npm install
   ```

2. Build the TypeScript code:
   ```
   npm run build
   ```

3. Start the server:
   ```
   npm start
   ```

   The server will run on port 3000 (configurable via `PORT` environment variable).

4. For development with auto-reload:
   ```
   npm run dev
   ```

## Testing

Run the test suite:
```
npm test
```

## API Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Filter by author
```bash
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a single book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated Edition)"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Data Validation

- `title` is required (non-empty string)
- `author` is required (non-empty string)
- `year` is optional (must be a valid integer)
- `isbn` is optional (string)

Invalid requests return HTTP 400 with an error message array.
