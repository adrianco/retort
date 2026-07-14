# Book Collection API

A small REST API for managing a book collection, built with **TypeScript**,
**Express**, and **SQLite** (via Node's built-in `node:sqlite` module). Tests are
written in a BDD (Given/When/Then) style with **Vitest** and **supertest**.

## Requirements

- Node.js 22.5+ (the embedded `node:sqlite` module; developed against Node 26)
- npm

## Setup

```bash
npm install
```

> No native compilation is needed — SQLite ships with Node via `node:sqlite`.

## Run

```bash
# Development (auto-reload)
npm run dev

# Production
npm run build
npm start
```

The server listens on port `3000` by default. Override with environment
variables:

- `PORT` — HTTP port (default `3000`)
- `DB_FILE` — SQLite database file (default `books.db`)

## Test

```bash
npm test
```

Tests run against an in-memory SQLite database, so they leave no files behind.

## API

All responses are JSON. A book has the shape:

```json
{ "id": 1, "title": "string", "author": "string", "year": 1999, "isbn": "string" }
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are optional.

| Method | Path           | Description                              | Success | Errors        |
| ------ | -------------- | ---------------------------------------- | ------- | ------------- |
| GET    | `/health`      | Health check                             | 200     | —             |
| POST   | `/books`       | Create a book                            | 201     | 400           |
| GET    | `/books`       | List books (optional `?author=` filter)  | 200     | —             |
| GET    | `/books/:id`   | Get a book by id                         | 200     | 400, 404      |
| PUT    | `/books/:id`   | Update a book                            | 200     | 400, 404      |
| DELETE | `/books/:id`   | Delete a book                            | 204     | 400, 404      |

### Examples

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'

# List all
curl http://localhost:3000/books

# Filter by author
curl 'http://localhost:3000/books?author=Andrew%20Hunt'

# Get by id
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer, 20th Anniversary Edition","author":"Andrew Hunt","year":2019}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project structure

```
src/
  db.ts          # SQLite connection + schema
  validation.ts  # request body validation
  repository.ts  # data-access layer (prepared statements)
  app.ts         # Express app + routes (DB injectable for tests)
  server.ts      # entry point
tests/
  books.test.ts  # BDD integration tests
```
