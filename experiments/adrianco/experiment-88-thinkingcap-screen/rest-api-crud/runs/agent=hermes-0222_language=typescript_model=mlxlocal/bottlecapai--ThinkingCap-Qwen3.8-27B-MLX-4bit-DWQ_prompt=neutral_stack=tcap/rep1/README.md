# Book Collection REST API

A REST API for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (via `better-sqlite3`).

## Endpoints

| Method | Path             | Description                                  | Success | Errors |
|--------|------------------|----------------------------------------------|---------|--------|
| GET    | `/health`        | Health check                                 | 200     | —      |
| POST   | `/books`         | Create a book (`title`, `author` required; `year`, `isbn` optional) | 201 | 400 |
| GET    | `/books`         | List all books; optional `?author=` filter   | 200     | —      |
| GET    | `/books/:id`     | Get a single book by ID                      | 200     | 400, 404 |
| PUT    | `/books/:id`     | Update a book (any subset of fields)         | 200     | 400, 404 |
| DELETE | `/books/:id`     | Delete a book                                | 204     | 404    |

All responses are JSON. Validation failures return `400` with `{ "error": "..." }`.

### Examples

```bash
# Create
curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}'

# List all / filter by author
curl http://localhost:8000/books
curl 'http://localhost:8000/books?author=J.R.R. Tolkien'

# Get one
curl http://localhost:8000/books/1

# Update
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1938}'

# Delete
curl -X DELETE http://localhost:8000/books/1

# Health
curl http://localhost:8000/health
```

## Setup

Requires Node.js 18+ (tested with Node 22).

```bash
npm install
```

## Run

Development (no build step, via tsx):

```bash
npm run dev
```

Production:

```bash
npm run build   # compiles TypeScript to dist/
npm start       # runs dist/server.js
```

Configuration via environment variables:

- `PORT` — port to listen on (default `8000`)
- `DB_PATH` — SQLite database file path (default `books.db`; data persists across restarts)

## Tests

Integration tests (Vitest) run the app on an ephemeral port with an in-memory SQLite database:

```bash
npm test
```

## Project layout

```
src/
  db.ts       SQLite setup + Book type
  app.ts      Express app factory, routes, validation
  server.ts   Entry point (reads PORT / DB_PATH)
tests/
  books.test.ts  Integration tests for all endpoints
```
