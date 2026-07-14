# Book API REST Service

A REST API for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` query parameter for filtering)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update an existing book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Tech Stack

- TypeScript 5
- Express 4
- better-sqlite3 (embedded SQLite)
- Jest + Supertest (testing)

## Setup and Run

### Prerequisites

- Node.js 18+
- npm

### Installation

```bash
npm install
```

### Build

```bash
npm run build
```

### Run

Development mode (with ts-node):
```bash
npm run dev
```

Production mode (compiled JavaScript):
```bash
npm start
```

The server starts on port 3456 by default. Set the `PORT` environment variable to use a different port.

## Testing

All tests (acceptance + unit):
```bash
npm test
```

Acceptance tests only:
```bash
npx jest tests/acceptance.test.ts
```

Unit tests only:
```bash
npx jest tests/unit.test.ts
```

## API Examples

### Health Check

```bash
curl http://localhost:3456/health
# {"status":"ok"}
```

### Create a Book

```bash
curl -X POST http://localhost:3456/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}
```

### List All Books

```bash
curl http://localhost:3456/books
# {"books":[{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}]}
```

### Filter by Author

```bash
curl "http://localhost:3456/books?author=Frank%20Herbert"
# {"books":[{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}]}
```

### Get a Book

```bash
curl http://localhost:3456/books/1
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}
```

### Update a Book

```bash
curl -X PUT http://localhost:3456/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune (Updated)","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# {"id":1,"title":"Dune (Updated)","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}
```

### Delete a Book

```bash
curl -X DELETE http://localhost:3456/books/1
# {"message":"Book deleted"}
```

## Validation

- `title` and `author` are required fields
- Missing title returns HTTP 400: `{"error":"title is required"}`
- Missing author returns HTTP 400: `{"error":"author is required"}`
- Non-existent book ID returns HTTP 404: `{"error":"Book not found"}`
