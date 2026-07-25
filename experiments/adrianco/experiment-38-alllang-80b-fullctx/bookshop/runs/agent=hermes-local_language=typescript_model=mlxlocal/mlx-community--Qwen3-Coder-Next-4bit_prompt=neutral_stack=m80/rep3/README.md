# Book API REST Service

A REST API service for managing a book collection using TypeScript, Express, and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/:id - Get a single book by ID
- PUT /books/:id - Update a book
- DELETE /books/:id - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn

## Installation

```bash
npm install
```

## Development

```bash
# Run in development mode (with ts-node)
npm run dev

# Build the project
npm run build

# Start the server
npm run start
```

## Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

## API Documentation

### GET /health

Returns the health status of the API.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### GET /books

Returns all books, optionally filtered by author.

**Query Parameters:**
- `author` (optional) - Filter books by author

**Response:**
```json
[
  {
    "id": 1,
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }
]
```

### GET /books/:id

Returns a single book by ID.

**Response:**
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Error Response (404):**
```json
{
  "error": "Book not found"
}
```

### POST /books

Creates a new book.

**Request Body:**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Required Fields:**
- `title` (string, required)
- `author` (string, required)

**Response (201):**
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Error Response (400):**
```json
{
  "error": "Title and author are required"
}
```

### PUT /books/:id

Updates an existing book.

**Request Body:**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Error Response (404):**
```json
{
  "error": "Book not found"
}
```

### DELETE /books/:id

Deletes a book by ID.

**Response (204):**
No content returned.

**Error Response (404):**
```json
{
  "error": "Book not found"
}
```

## Project Structure

```
src/
├── server.ts          # Main entry point
├── routes/
│   └── books.ts       # Book routes
├── controllers/
│   └── books.ts       # Book controllers
├── models/
│   └── book.ts        # Book model and database operations
├── middleware/
│   └── validation.ts  # Input validation middleware
├── database.ts        # Database connection
└── types.ts           # TypeScript type definitions
tests/
├── books.test.ts      # Book API tests
└── health.test.ts     # Health check tests
```

## License

ISC
