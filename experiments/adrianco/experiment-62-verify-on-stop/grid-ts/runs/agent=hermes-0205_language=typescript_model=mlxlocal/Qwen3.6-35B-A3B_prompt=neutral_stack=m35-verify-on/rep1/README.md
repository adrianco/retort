# Book Collection REST API

A TypeScript REST API service for managing a book collection, built with Express and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports ?author= filter)
- **GET /books/:id** - Get a single book by ID
- **PUT /books/:id** - Update a book
- **DELETE /books/:id** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Node.js >= 18
- npm

## Setup

1. Install dependencies:

```bash
npm install
```

2. Build the project:

```bash
npm run build
```

3. Start the server:

```bash
npm start
```

The API will be available at `http://localhost:3000`.

To run in development mode with auto-reload:

```bash
npm run dev
```

## Testing

Run the test suite:

```bash
npm test
```

## API Endpoints

### GET /health

Returns the health status of the API.

**Response:**

```json
{ "status": "ok" }
```

### POST /books

Creates a new book.

**Request body:**

```json
{
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

- `title` and `author` are required.
- `year` and `isbn` are optional.

**Response (201 Created):**

```json
{ "id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935" }
```

**Response (400 Bad Request) - missing required fields:**

```json
{ "error": "title and author are required" }
```

### GET /books

Lists all books. Supports optional `?author=` query parameter to filter by author.

**Response (200 OK):**

```json
[
  { "id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935" },
  { "id": 2, "title": "Animal Farm", "author": "George Orwell", "year": 1945, "isbn": null }
]
```

### GET /books/:id

Returns a single book by ID.

**Response (200 OK):**

```json
{ "id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935" }
```

**Response (404 Not Found):**

```json
{ "error": "Book not found" }
```

### PUT /books/:id

Updates an existing book.

**Request body:**

```json
{
  "title": "Nineteen Eighty-Four",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

**Response (200 OK):**

```json
{ "id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935" }
```

### DELETE /books/:id

Deletes a book by ID.

**Response (204 No Content):** Empty body.

**Response (404 Not Found):**

```json
{ "error": "Book not found" }
```

## Project Structure

```
src/
  app.ts        - Express app with all API routes
  server.ts     - Server entry point (db setup + listen)
tests/
  app.test.ts   - Comprehensive test suite (16 tests)
package.json
tsconfig.json
jest.config.js
```
