# Book Collection API

A small REST API for managing a collection of books, built with **TypeScript**,
**Express**, and the built-in **`node:sqlite`** embedded database (no native
build step required).

## Requirements

- Node.js **22.5+** (uses the built-in `node:sqlite` module; developed on Node 24)

## Setup

```bash
npm install
```

## Run

```bash
# Development (auto-reload, runs from TypeScript source)
npm run dev

# Production
npm run build
npm start
```

The server listens on `http://localhost:3000` by default. Configure via
environment variables:

- `PORT` — HTTP port (default `3000`)
- `DB_PATH` — SQLite file path (default `books.db`; use `:memory:` for ephemeral)

## Tests

```bash
npm test
```

Tests run against an in-memory database using Node's built-in test runner
(`node:test`) + Supertest, executed directly from TypeScript via `tsx`.

## API

A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are optional.

| Method | Path           | Description                              | Success | Errors |
|--------|----------------|------------------------------------------|---------|--------|
| GET    | `/health`      | Health check                             | 200     | —      |
| POST   | `/books`       | Create a book                            | 201     | 400    |
| GET    | `/books`       | List books (optional `?author=` filter)  | 200     | —      |
| GET    | `/books/{id}`  | Get a book by id                         | 200     | 400, 404 |
| PUT    | `/books/{id}`  | Replace/update a book                    | 200     | 400, 404 |
| DELETE | `/books/{id}`  | Delete a book                            | 204     | 400, 404 |

Validation failures return `{ "errors": [ ... ] }`; not-found and bad-id
errors return `{ "error": "..." }`.

### Examples

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all / filter by author
curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project structure

```
src/
  db.ts       # SQLite schema + BookRepository data access
  app.ts      # Express app factory, routes, validation
  server.ts   # Entry point (wires DB + app, starts listening)
test/
  books.test.ts
```
