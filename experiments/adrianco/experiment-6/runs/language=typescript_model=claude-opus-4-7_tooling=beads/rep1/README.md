# Book Collection API

A small REST API for managing a book collection, written in TypeScript with
Express and SQLite (via `better-sqlite3`).

## Requirements

- Node.js 18+ (developed against Node 22)
- npm

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

The server listens on port `3000` by default. Override with environment variables:

- `PORT` — port to bind (default `3000`)
- `DB_PATH` — SQLite database file path (default `books.db`)

For development with auto-reload via `ts-node`:

```bash
npm run dev
```

## Test

```bash
npm test
```

Tests use an in-memory SQLite database, so they do not touch the filesystem.

## Endpoints

| Method | Path           | Description                                   |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Health check — returns `{ "status": "ok" }`   |
| POST   | `/books`       | Create a book                                 |
| GET    | `/books`       | List all books (optional `?author=` filter)   |
| GET    | `/books/{id}`  | Get a single book by id                       |
| PUT    | `/books/{id}`  | Replace a book by id                          |
| DELETE | `/books/{id}`  | Delete a book by id                           |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

- `title` (string, required, non-empty)
- `author` (string, required, non-empty)
- `year` (integer, optional)
- `isbn` (string, optional)

### Examples

```bash
# Create
curl -sX POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List
curl -s http://localhost:3000/books
curl -s 'http://localhost:3000/books?author=Frank%20Herbert'

# Get one
curl -s http://localhost:3000/books/1

# Update
curl -sX PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# Delete
curl -sX DELETE http://localhost:3000/books/1
```

### Status codes

- `200 OK` — successful read/update
- `201 Created` — successful create
- `204 No Content` — successful delete
- `400 Bad Request` — invalid id or invalid/missing fields
- `404 Not Found` — book id does not exist

## Project layout

```
src/
  app.ts          Express app factory and route handlers
  db.ts           SQLite-backed BookStore
  validation.ts   Input validation and id parsing
  server.ts       Entry point — binds the HTTP server
tests/
  api.test.ts     Integration tests (supertest + in-memory DB)
```
