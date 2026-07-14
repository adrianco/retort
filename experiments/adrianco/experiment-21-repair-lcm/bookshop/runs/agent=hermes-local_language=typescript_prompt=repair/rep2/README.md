# Book Collection REST API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Node.js >= 18
- npm >= 9

## Setup

```bash
# Install dependencies
npm install

# Build the project
npm run build
```

## Running

```bash
# Start the server
npm start
```

The server will start on port 3000 by default. Set the `PORT` environment variable to use a different port.

## Testing

```bash
npm test
```

Runs the full test suite using Jest.

## API Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Filter books by author
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
  -d '{"title":"Updated Title"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Tech Stack

- **TypeScript** — Type-safe JavaScript
- **Express** — Fast, minimalist web framework
- **better-sqlite3** — Synchronous, fast SQLite bindings
- **Jest + Supertest** — Testing framework and HTTP testing
- **ts-jest** — TypeScript support for Jest
