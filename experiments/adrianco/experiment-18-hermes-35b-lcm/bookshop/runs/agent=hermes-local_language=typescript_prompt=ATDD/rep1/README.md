# Book Collection REST API

A TypeScript REST API service for managing a book collection, built with Express and SQLite.

## Features

- Full CRUD operations for books (Create, Read, Update, Delete)
- Filter books by author via query parameter
- Input validation (title and author are required)
- SQLite database for persistent data storage
- Health check endpoint
- 21 acceptance tests covering all endpoints

## Prerequisites

- Node.js >= 18
- npm

## Setup

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

   The server will start on http://localhost:3000.

   For development with auto-reload:
   ```bash
   npm run dev
   ```

## Running Tests

All tests are acceptance tests written from the perspective of an external HTTP client:

```bash
npm test
```

Tests run in isolation -- each test suite creates its own in-memory database to ensure atomic, independent scenarios.

## API Endpoints

### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{ "status": "ok" }
```

### POST /books

Create a new book.

**Request body:**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```
- `title` (required) and `author` (required) must be present and non-empty.
- `year` and `isbn` are optional.

**Response (201 Created):**
```json
{ "id": "550e8400-e29b-41d4-a716-446655440000", "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565" }
```

**Response (400 Bad Request) - validation error:**
```json
{ "error": "title is required" }
```

### GET /books

List all books. Optionally filter by author.

**Query parameters:**
- `author` (optional) -- filter results to only books by this author.

**Response (200 OK):**
```json
[
  { "id": "...", "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565" },
  { "id": "...", "title": "1984", "author": "George Orwell", "year": 1949, "isbn": null }
]
```

### GET /books/:id

Get a single book by its ID.

**Response (200 OK):**
```json
{ "id": "...", "title": "To Kill a Mockingbird", "author": "Harper Lee", "year": 1960, "isbn": "978-0061120084" }
```

**Response (404 Not Found):**
```json
{ "error": "Book not found" }
```

### PUT /books/:id

Update an existing book. The `title` and `author` fields are always required in the request body.

**Request body:**
```json
{ "title": "Updated Title", "author": "Updated Author", "year": 2023 }
```

**Response (200 OK):**
```json
{ "id": "...", "title": "Updated Title", "author": "Updated Author", "year": 2023, "isbn": "978-0743273565" }
```

**Response (400 Bad Request) - validation error:**
```json
{ "error": "title is required" }
```

**Response (404 Not Found):**
```json
{ "error": "Book not found" }
```

### DELETE /books/:id

Delete a book by its ID.

**Response (200 OK):**
```json
{ "id": "...", "title": "Deleted Book", "author": "Gone", "year": null, "isbn": null }
```

**Response (404 Not Found):**
```json
{ "error": "Book not found" }
```

## Project Structure

```
├── src/
│   ├── app.ts          # Express application with all REST endpoints
│   └── database.ts     # SQLite database layer (better-sqlite3)
├── tests/
│   └── acceptance.test.ts  # 21 acceptance tests (API-level only)
├── package.json
├── tsconfig.json
├── vitest.config.ts
└── README.md
```

## ATDD Approach

This project follows Acceptance Test-Driven Development. All 21 acceptance tests were written first, testing the service purely through its HTTP API with no back-door access to internals. Tests are atomic and independent -- each test suite creates its own isolated database.
