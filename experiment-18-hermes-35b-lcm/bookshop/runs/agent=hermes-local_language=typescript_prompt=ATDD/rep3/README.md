# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **Create** books with title, author, year, and ISBN
- **List** all books, optionally filtered by author (`?author=`)
- **Retrieve** a single book by ID
- **Update** an existing book
- **Delete** a book
- **Health check** endpoint at `/health`
- Input validation: title and author are required
- In-memory SQLite database for testing

## Tech Stack

- **TypeScript** - Strongly typed source code
- **Express** - HTTP server framework
- **better-sqlite3** - Embedded SQLite database
- **Mocha + Chai + Supertest** - Testing framework

## Getting Started

### Prerequisites

- Node.js 18+
- npm 9+

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

The server starts on port 3000 (or the PORT environment variable).

### Run Tests

```bash
npm test
```

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{ "status": "ok" }
```

### Create a Book

```
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

Response (201 Created):
```json
{ "id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565" }
```

Validation: `title` and `author` are required. Returns 400 if missing.

### List Books

```
GET /books
GET /books?author=F.%20Scott%20Fitzgerald
```

Response (200 OK):
```json
[ { "id": 1, "title": "...", "author": "...", "year": 1925, "isbn": "..." } ]
```

### Get a Book

```
GET /books/1
```

Response (200 OK) or 404 if not found.

### Update a Book

```
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby (Updated)",
  "author": "F. Scott Fitzgerald",
  "year": 2023,
  "isbn": "978-0743273565"
}
```

Response (200 OK) with the updated book. Title and author are required on update.

### Delete a Book

```
DELETE /books/1
```

Response (200 OK) with the deleted book object, or 404 if not found.

## Testing

The project uses Acceptance Test-Driven Development (ATDD):

- **17 acceptance tests** — exercise the REST API as an external client would
- **4 unit/integration tests** — cover trimming, defaults, and full CRUD workflows

All tests are independent: each test creates its own fresh in-memory database and shares no state with other tests.

```bash
npm test
```
