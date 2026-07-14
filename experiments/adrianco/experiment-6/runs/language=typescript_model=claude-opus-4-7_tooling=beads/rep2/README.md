# Books API

A small REST API for managing a book collection, built with TypeScript, Express, and SQLite (`better-sqlite3`).

## Requirements

- Node.js 18+ (developed against Node 24)
- npm

## Setup

```bash
npm install
npm run build
```

## Running

```bash
# Production: compile, then run
npm run build
npm start

# Development: run directly with ts-node
npm run dev
```

Environment variables:

- `PORT` — listening port (default `3000`)
- `DB_FILE` — SQLite file path (default `books.db`; use `:memory:` for ephemeral)

## Tests

```bash
npm test
```

Tests use an in-memory SQLite database, so no cleanup is needed.

## Endpoints

| Method | Path              | Description                                |
|--------|-------------------|--------------------------------------------|
| GET    | `/health`         | Liveness probe                             |
| POST   | `/books`          | Create a book                              |
| GET    | `/books`          | List books; optional `?author=` filter     |
| GET    | `/books/:id`      | Fetch a single book by id                  |
| PUT    | `/books/:id`      | Replace a book                             |
| DELETE | `/books/:id`      | Delete a book                              |

### Book schema

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

`title` and `author` are required (non-empty strings). `year` (integer) and `isbn` (string) are optional.

### Status codes

- `200 OK` — successful read or update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — invalid input / malformed JSON
- `404 Not Found` — unknown book id

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'
curl http://localhost:3000/books/1

curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
src/
  db.ts       # BookStore (SQLite-backed)
  app.ts      # Express app + routes + validation
  server.ts   # Entry point
tests/
  books.test.ts
```
