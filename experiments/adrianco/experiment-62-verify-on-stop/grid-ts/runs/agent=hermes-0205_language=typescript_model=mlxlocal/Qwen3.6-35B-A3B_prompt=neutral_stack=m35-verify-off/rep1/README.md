# Book Collection REST API

A TypeScript REST API service for managing a book collection, backed by SQLite.

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

## Setup and Run

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Start the server
npm start
```

The server will start on port 3000 by default. Set the `PORT` environment variable to use a different port.

For development with auto-reload:

```bash
npm run dev
```

## Testing

```bash
npm test
```

Runs 23 integration tests using Jest and Supertest with 95%+ code coverage.

## API Examples

### Create a book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### List all books

```bash
curl http://localhost:3000/books
```

### Filter by author

```bash
curl "http://localhost:3000/books?author=George+Orwell"
```

### Get a book by ID

```bash
curl http://localhost:3000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check

```bash
curl http://localhost:3000/health
```

## Validation

- `title` and `author` are required fields (non-empty strings)
- `year` must be a valid integer between 0 and current year + 1
- `isbn` is optional
- Book ID must be a positive integer

## Tech Stack

- **TypeScript** — Type-safe language
- **Express** — Web framework
- **better-sqlite3** — Embedded SQLite database
- **Jest + Supertest** — Testing framework
