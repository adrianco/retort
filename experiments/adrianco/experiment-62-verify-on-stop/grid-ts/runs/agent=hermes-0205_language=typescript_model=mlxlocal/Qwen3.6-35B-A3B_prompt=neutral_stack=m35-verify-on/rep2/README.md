# Book Collection API

A REST API service for managing a book collection, built with Node.js, Express, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation with detailed error messages
- SQLite database for persistent storage
- Health check endpoint

## API Endpoints

| Method | Endpoint           | Description                    |
|--------|--------------------|--------------------------------|
| GET    | /health            | Health check                   |
| POST   | /api/books         | Create a new book              |
| GET    | /api/books         | List all books (optional ?author= filter) |
| GET    | /api/books/:id     | Get a single book by ID        |
| PUT    | /api/books/:id     | Update a book                  |
| DELETE | /api/books/:id     | Delete a book                  |

### Book Schema

```json
{
  "title": "string (required)",
  "author": "string (required)",
  "year": "number (required, integer)",
  "isbn": "string (required, unique)"
}
```

### Response Codes

- 200 - Success
- 201 - Created
- 204 - No Content (delete)
- 400 - Bad Request (validation error)
- 404 - Not Found
- 409 - Conflict (duplicate ISBN)
- 500 - Internal Server Error

## Setup and Run

### Prerequisites

- Node.js >= 18
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

```bash
npm start
```

The server will start on port 3000 (or the port specified by the `PORT` environment variable).

### Run Tests

```bash
npm test
```

## Project Structure

```
src/
  app.js          - Express app setup and middleware
  db.js           - SQLite database layer
  routes.js       - API route handlers
  server.js       - Server entry point
  __tests__/
    api.test.js   - Integration tests
```
