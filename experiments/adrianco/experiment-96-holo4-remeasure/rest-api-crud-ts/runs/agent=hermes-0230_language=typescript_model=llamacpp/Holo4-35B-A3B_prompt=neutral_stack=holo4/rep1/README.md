# Book API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Setup

```bash
npm install
```

## Running

```bash
# Development mode (with ts-node)
npm run dev

# Production mode (build first)
npm run build
npm start
```

The server starts on port 3000 by default.

## Testing

```bash
npm test
```

## API Examples

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=F. Scott Fitzgerald"

# Get a book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```
