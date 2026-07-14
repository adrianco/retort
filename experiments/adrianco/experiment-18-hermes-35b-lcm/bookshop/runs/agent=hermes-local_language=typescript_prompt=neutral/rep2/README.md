# Book API REST Service

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (supports ?author= query filter)
- GET /books/:id — Get a single book by ID
- PUT /books/:id — Update a book
- DELETE /books/:id — Delete a book
- GET /health — Health check endpoint

All endpoints return JSON responses with appropriate HTTP status codes. Input validation ensures title and author are required fields.

## Technical Stack

- **Language:** TypeScript
- **Framework:** Express.js
- **Database:** SQLite (via sqlite3)
- **Testing:** Jest + Supertest

## Prerequisites

- Node.js >= 18.x
- npm >= 9.x

## Setup and Run

1. Install dependencies:
   ```bash
   npm install
   ```

2. Build the TypeScript code:
   ```bash
   npm run build
   ```

3. Start the server:
   ```bash
   npm start
   ```

   The server will listen on port 3000 by default. To use a different port:
   ```bash
   PORT=8080 npm start
   ```

   The database file defaults to `books.db` in the project root. To use a custom path:
   ```bash
   DB_PATH=/path/to/books.db npm start
   ```

## Running Tests

```bash
npm test
```

Tests use an in-memory SQLite database.

## API Reference

### POST /books

Create a new book.

**Request body:**
```json
{
  "title": "string (required)",
  "author": "string (required)",
  "year": "number (required, integer)",
  "isbn": "string (required, unique)"
}
```

**Responses:**
- `201` — Book created successfully
- `400` — Validation error (missing/invalid fields)
- `409` — ISBN already exists

### GET /books

List all books. Optionally filter by author.

**Query parameters:**
- `author` (optional) — Filter by author name

**Responses:**
- `200` — Array of books

### GET /books/:id

Get a single book by ID.

**Responses:**
- `200` — Book object
- `400` — Invalid ID format
- `404` — Book not found

### PUT /books/:id

Update an existing book. Only provide the fields you want to update.

**Request body:**
```json
{
  "title": "string (optional)",
  "author": "string (optional)",
  "year": "number (optional, integer)",
  "isbn": "string (optional, unique)"
}
```

**Responses:**
- `200` — Updated book object
- `400` — Validation error
- `404` — Book not found
- `409` — ISBN already exists

### DELETE /books/:id

Delete a book by ID.

**Responses:**
- `200` — Book deleted successfully
- `404` — Book not found

### GET /health

Health check endpoint.

**Responses:**
- `200` — `{"status": "ok", "timestamp": "ISO-8601 string"}`

## Example

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"

# Get a specific book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":1926}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```
