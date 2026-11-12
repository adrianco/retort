# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id} — Delete a book
- **GET /health** — Health check endpoint

## Setup

```bash
npm install
```

## Running

```bash
# Build and run
npm run build
npm start

# Or run in development mode
npm run dev
```

The server will start on port 3000.

## Testing

```bash
npm test
```

## API Endpoints

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

**Response:** 201 Created with the created book object.

### GET /books
List all books.

**Query params:**
- `author` (optional) — Filter books by author name

**Response:** 200 OK with array of book objects.

### GET /books/:id
Get a single book by ID.

**Response:** 200 OK with book object, or 404 if not found.

### PUT /books/:id
Update a book.

**Request body (all fields optional):**
```json
{
  "title": "New Title",
  "author": "New Author",
  "year": 2024,
  "isbn": "978-0743273565"
}
```

**Response:** 200 OK with updated book object.

### DELETE /books/:id
Delete a book.

**Response:** 204 No Content, or 404 if not found.

### GET /health
Health check.

**Response:** 200 OK with `{"status": "OK"}`.
