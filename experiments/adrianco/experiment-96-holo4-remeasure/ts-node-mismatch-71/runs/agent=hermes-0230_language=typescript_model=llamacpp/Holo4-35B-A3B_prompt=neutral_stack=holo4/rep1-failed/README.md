# Book API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST** `/api/books` — Create a new book (title, author, year, isbn)
- **GET** `/api/books` — List all books (supports `?author=` filter)
- **GET** `/api/books/:id` — Get a single book by ID
- **PUT** `/api/books/:id` — Update a book
- **DELETE** `/api/books/:id` — Delete a book
- **GET** `/api/health` — Health check endpoint

## Setup

```bash
npm install
```

## Running

```bash
# Development (with ts-node)
npm run dev

# Build and run
npm run build
npm start
```

The server starts on port 3000 by default.

## Tests

```bash
npm test
```

## API Examples

```bash
# Create a book
curl -X POST http://localhost:3000/api/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'

# List all books
curl http://localhost:3000/api/books

# Filter by author
curl "http://localhost:3000/api/books?author=F. Scott Fitzgerald"

# Get a book
curl http://localhost:3000/api/books/1

# Update a book
curl -X PUT http://localhost:3000/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)"}'

# Delete a book
curl -X DELETE http://localhost:3000/api/books/1
```
