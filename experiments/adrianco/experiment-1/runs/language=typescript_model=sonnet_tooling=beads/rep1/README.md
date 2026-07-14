# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite (via better-sqlite3).

## Setup

```bash
npm install
```

## Running

### Development (ts-node)
```bash
npm run dev
```

### Production
```bash
npm run build
npm start
```

The server listens on port `3000` by default. Set the `PORT` environment variable to override.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/:id | Get a book by ID |
| PUT | /books/:id | Update a book |
| DELETE | /books/:id | Delete a book |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0-441-17271-9",
  "created_at": "2026-04-13 00:00:00",
  "updated_at": "2026-04-13 00:00:00"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Examples

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# List books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=Herbert"

# Get a book
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1965}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```

## Tests

```bash
npm test
```

Runs 12 integration tests covering all endpoints using an in-memory SQLite database.
