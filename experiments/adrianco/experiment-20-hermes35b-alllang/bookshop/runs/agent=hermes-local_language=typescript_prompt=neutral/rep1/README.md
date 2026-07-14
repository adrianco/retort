# Book API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite database with WAL mode for concurrency

## Prerequisites

- Node.js 18+
- npm

## Setup

```bash
npm install
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
```

The server starts on port 3000 by default. Set the PORT environment variable to change it:

```bash
PORT=8080 npm start
```

## API Endpoints

| Method | Endpoint       | Description                  |
|--------|----------------|------------------------------|
| GET    | /health        | Health check                 |
| POST   | /books         | Create a new book            |
| GET    | /books         | List all books               |
| GET    | /books/:id     | Get a book by ID             |
| PUT    | /books/:id     | Update a book                |
| DELETE | /books/:id     | Delete a book                |

### POST /books

Request body:

```json
{
  "title": "string (required)",
  "author": "string (required)",
  "year": "number (optional)",
  "isbn": "string (optional)"
}
```

Response (201 Created):

```json
{
  "id": "uuid",
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### GET /books

Query parameters:

- `author` - Filter books by author name

Response (200 OK):

```json
[
  {
    "id": "uuid",
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }
]
```

### GET /books/:id

Response (200 OK):

```json
{
  "id": "uuid",
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### PUT /books/:id

Request body (all fields optional, but at least title or author must be valid):

```json
{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 1926,
  "isbn": "978-0743273566"
}
```

### DELETE /books/:id

Response (200 OK):

```json
{
  "message": "Book deleted successfully"
}
```

## Error Responses

- 400 Bad Request - Validation errors
- 404 Not Found - Book not found
- 409 Conflict - ISBN already exists
- 500 Internal Server Error - Server error

## Testing

```bash
npm test
```

Tests use Jest and Supertest. The test suite creates fresh in-memory databases for each test.
