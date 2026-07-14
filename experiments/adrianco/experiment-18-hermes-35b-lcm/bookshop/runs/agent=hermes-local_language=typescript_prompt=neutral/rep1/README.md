# Book Collection REST API

A REST API service for managing a book collection, built with TypeScript, Express, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/:id** — Get a single book by ID
- **PUT /books/:id** — Update a book
- **DELETE /books/:id** — Delete a book
- **GET /health** — Health check endpoint

## Tech Stack

- TypeScript
- Express.js
- better-sqlite3 (embedded SQLite database)

## Setup and Run

1. Install dependencies:
   ```bash
   npm install
   ```

2. Build TypeScript:
   ```bash
   npm run build
   ```

3. Start the server:
   ```bash
   npm start
   ```

   The server runs on port 3000 by default (configurable via `PORT` environment variable).

   For development with live reload during code changes:
   ```bash
   npm run dev
   ```

## Testing

Run the test suite:
```bash
npm test
```

The tests cover:
- Health check validation
- Book creation with valid and invalid data
- Full CRUD operations (list, get, update, delete)
- Author filtering
- Error handling (404, 400 cases)

## API Examples

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"

# Get a single book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"New Author","year":2024,"isbn":"978-0743273566"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1

# Health check
curl http://localhost:3000/health
```

## Project Structure

```
├── src/
│   ├── app.ts              # Express application and routes
│   ├── database.ts         # SQLite database setup
│   ├── routes/
│   │   └── books.ts        # Book CRUD logic and validation
│   ├── better-sqlite3.d.ts # Type declarations for better-sqlite3
├── tests/
│   └── app.test.ts         # Integration tests
├── package.json
├── tsconfig.json
├── jest.config.js
└── README.md
```
