# Book Collection API

A small REST service for managing a collection of books, written in TypeScript
with [Express 5](https://expressjs.com/) and SQLite (via Node's built-in
`node:sqlite` module, so there is no native build step).

## Requirements

- Node.js 22.13 or newer (tested on Node 26). `node:sqlite` ships with Node.
- npm

## Setup

```bash
npm install
```

## Run

```bash
# Development (auto-reload on change)
npm run dev

# Production build + start
npm run build
npm start
```

The server listens on `http://localhost:3000` by default.

| Variable  | Default    | Purpose                                                 |
|-----------|------------|---------------------------------------------------------|
| `PORT`    | `3000`     | TCP port to listen on                                   |
| `DB_PATH` | `books.db` | SQLite file path. Use `:memory:` for an ephemeral store |

## Test

```bash
npm test          # runs the Vitest suite (Supertest against the in-memory DB)
npm run typecheck # tsc --noEmit
```

## API

All responses are JSON. Errors have the shape `{ "error": "...", "details"?: [...] }`.

| Method   | Path             | Description                                   | Success |
|----------|------------------|-----------------------------------------------|---------|
| `GET`    | `/health`        | Liveness + database check                     | `200`   |
| `POST`   | `/books`         | Create a book                                 | `201`   |
| `GET`    | `/books`         | List books; optional `?author=` filter        | `200`   |
| `GET`    | `/books/{id}`    | Fetch one book                                | `200`   |
| `PUT`    | `/books/{id}`    | Replace a book (full update)                  | `200`   |
| `DELETE` | `/books/{id}`    | Delete a book                                 | `204`   |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "createdAt": "2026-09-01T21:10:00.123Z",
  "updatedAt": "2026-09-01T21:10:00.123Z"
}
```

### Validation rules

- `title` and `author` are required non-empty strings (trimmed, max 500 chars).
- `year` is optional; if present it must be an integer between -3000 and five years from now.
- `isbn` is optional; if present it must be a valid ISBN-10 or ISBN-13 (hyphens/spaces allowed).
  It is stored and returned in normalized form (separators removed, e.g. `9780441013593`)
  and must be unique across the collection, so `978-0441013593` and `9780441013593` collide.
- `PUT` is a full replacement: omitted `year`/`isbn` are stored as `null`.
- The `?author=` filter is an exact, case-insensitive match.

### Status codes

| Code  | When                                                        |
|-------|-------------------------------------------------------------|
| `400` | Validation failure, malformed JSON, or non-numeric `{id}`   |
| `404` | Unknown book id or unknown route                            |
| `409` | ISBN already belongs to another book                        |
| `413` | Body larger than 100 KB                                     |
| `500` | Unexpected server error                                     |

### Examples

```bash
curl -s localhost:3000/health

curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl -s 'localhost:3000/books?author=Frank%20Herbert'

curl -s localhost:3000/books/1

curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -s -X DELETE localhost:3000/books/1 -i
```

## Project layout

```
src/
  app.ts          Express app factory (routes, validation wiring, error handling)
  db.ts           SQLite schema, BookRepository
  validation.ts   Input validation helpers (book body, ISBN, id)
  server.ts       Entrypoint: opens DB, starts HTTP server, graceful shutdown
tests/
  books.test.ts       HTTP integration tests (Supertest)
  validation.test.ts  Unit tests for validation helpers
```
