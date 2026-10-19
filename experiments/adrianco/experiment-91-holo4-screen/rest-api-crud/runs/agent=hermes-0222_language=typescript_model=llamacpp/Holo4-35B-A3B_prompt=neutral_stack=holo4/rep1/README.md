# Book API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Setup

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Start the server
npm start
```

The server will start on port 3000 (or the port specified by the `PORT` environment variable).

## Running Tests

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

**Response:** `201 Created` with the created book object.

### GET /books
List all books.

**Query parameters:**
- `author` (optional) — Filter books by author name

**Response:** `200 OK` with an array of book objects.

### GET /books/:id
Get a single book by ID.

**Response:** `200 OK` with the book object, or `404 Not Found`.

### PUT /books/:id
Update a book. Only provided fields are updated.

**Request body:**
```json
{
  "title": "The Great Gatsby (Updated Edition)"
}
```

**Response:** `200 OK` with the updated book object.

### DELETE /books/:id
Delete a book.

**Response:** `204 No Content` on success, or `404 Not Found`.

### GET /health
Health check endpoint.

**Response:** `200 OK` with `{ "status": "ok", "timestamp": "..." }`.
