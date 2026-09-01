# Book Collection API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- **Language**: TypeScript
- **Framework**: Express.js
- **Database**: SQLite (via better-sqlite3)
- **Testing**: Jest + Supertest

## Setup and Run

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

   The server will be available at `http://localhost:3000`

4. For development with auto-reload:
   ```bash
   npm run dev
   ```

## Testing

Run the test suite:
```bash
npm test
```

## API Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Filter by author
```bash
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "year": 1925, "isbn": "978-0743273565"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Validation

- `title` and `author` are required fields when creating or updating a book
- Returns appropriate HTTP status codes:
  - `201` — Created
  - `200` — OK
  - `204` — No Content (delete success)
  - `400` — Bad Request (validation error)
  - `404` — Not Found
