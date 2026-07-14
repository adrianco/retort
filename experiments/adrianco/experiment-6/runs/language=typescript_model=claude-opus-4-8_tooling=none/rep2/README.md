# Book Collection API

A small REST API for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (via `better-sqlite3`).

## Requirements

- Node.js 18+ (developed against Node 24)
- npm

## Setup

```bash
npm install
```

## Running

Development (TypeScript directly, no build step):

```bash
npm run dev
```

Production (compile to `dist/` then run):

```bash
npm run build
npm start
```

The server listens on port `3000` by default. Override with environment variables:

- `PORT` — HTTP port (default `3000`)
- `DB_FILE` — SQLite file path (default `books.db`)

## Testing

```bash
npm test
```

Tests use an in-memory SQLite database and exercise every endpoint via HTTP (`supertest`).

## API

All responses are JSON. A `book` looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are optional.

| Method | Path           | Description                              | Success | Errors            |
| ------ | -------------- | ---------------------------------------- | ------- | ----------------- |
| GET    | `/health`      | Health check                             | 200     | —                 |
| POST   | `/books`       | Create a book                            | 201     | 400 (validation)  |
| GET    | `/books`       | List books (optional `?author=` filter)  | 200     | —                 |
| GET    | `/books/:id`   | Get a single book                        | 200     | 400, 404          |
| PUT    | `/books/:id`   | Update a book                            | 200     | 400, 404          |
| DELETE | `/books/:id`   | Delete a book                            | 204     | 400, 404          |

### Examples

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List (all)
curl http://localhost:3000/books

# List (filter by author)
curl 'http://localhost:3000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project structure

```
src/
  db.ts          # SQLite setup + Book type
  app.ts         # Express app factory with all routes + validation
  server.ts      # Entry point (starts the HTTP server)
  app.test.ts    # Integration tests (supertest + in-memory DB)
```
