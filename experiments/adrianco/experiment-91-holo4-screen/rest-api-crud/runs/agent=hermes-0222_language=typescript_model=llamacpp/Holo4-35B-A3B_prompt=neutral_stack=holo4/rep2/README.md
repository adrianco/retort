# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST** `/books` — Create a new book (title, author, year, isbn)
- **GET** `/books` — List all books (supports `?author=` filter)
- **GET** `/books/:id` — Get a single book by ID
- **PUT** `/books/:id` — Update a book
- **DELETE** `/books/:id` — Delete a book
- **GET** `/health` — Health check endpoint

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

The server starts on port 3000 by default (configurable via `PORT` env variable).

## Testing

```bash
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

### List books by author
```bash
curl "http://localhost:3000/books?author=F. Scott Fitzgerald"
```

### Get a book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```
