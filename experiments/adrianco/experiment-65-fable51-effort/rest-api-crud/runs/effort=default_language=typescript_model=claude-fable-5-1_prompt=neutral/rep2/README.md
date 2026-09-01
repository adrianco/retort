# Book Collection API

A small REST service for managing a collection of books, written in TypeScript
with [Express 5](https://expressjs.com/) and SQLite (via Node's built-in
`node:sqlite` module, so there is nothing native to compile).

## Requirements

- Node.js **22.13 or newer** (uses the built-in `node:sqlite` module)
- npm

## Setup

```bash
npm install
```

## Run

Development (auto-reload on change):

```bash
npm run dev
```

Production build:

```bash
npm run build
npm start
```

The server listens on `http://localhost:3000` by default.

| Environment variable | Default    | Purpose                                            |
| -------------------- | ---------- | -------------------------------------------------- |
| `PORT`               | `3000`     | TCP port to listen on                              |
| `DB_PATH`            | `books.db` | SQLite file path (use `:memory:` for an ephemeral DB) |

## Test

```bash
npm test          # runs the Vitest suite (API integration + repository unit tests)
npm run typecheck # type-check without emitting
```

## API

All requests and responses are JSON.

| Method   | Path              | Description                              | Success |
| -------- | ----------------- | ---------------------------------------- | ------- |
| `GET`    | `/health`         | Health check (verifies DB connectivity)  | `200`   |
| `POST`   | `/books`          | Create a book                            | `201`   |
| `GET`    | `/books`          | List books; optional `?author=` filter   | `200`   |
| `GET`    | `/books/{id}`     | Get one book                             | `200`   |
| `PUT`    | `/books/{id}`     | Replace a book (full update)             | `200`   |
| `DELETE` | `/books/{id}`     | Delete a book                            | `204`   |

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "createdAt": "2026-09-01T12:00:00.000Z",
  "updatedAt": "2026-09-01T12:00:00.000Z"
}
```

Request body for `POST` and `PUT`:

| Field    | Type    | Required | Notes                                                        |
| -------- | ------- | -------- | ------------------------------------------------------------ |
| `title`  | string  | yes      | Non-blank, at most 500 characters                            |
| `author` | string  | yes      | Non-blank, at most 500 characters                            |
| `year`   | integer | no       | Between -3000 and five years from now                        |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13; hyphens/spaces are stripped; must be unique |

Unknown fields are rejected. `PUT` is a full replacement: omitted optional
fields are set to `null`.

The `?author=` filter is a case-insensitive exact match.

### Error responses

| Status | When                                                     | Shape                                                     |
| ------ | -------------------------------------------------------- | --------------------------------------------------------- |
| `400`  | Validation failure, bad `id`, or malformed JSON           | `{ "error": "Validation Error", "details": [{ "field", "message" }] }` or `{ "error": "Bad Request", "message" }` |
| `404`  | Book or route not found                                  | `{ "error": "Not Found", "message" }`                     |
| `409`  | ISBN already belongs to another book                     | `{ "error": "Conflict", "message" }`                      |
| `413`  | Body larger than 100 KB                                  | `{ "error": "Payload Too Large", "message" }`             |
| `500`  | Unexpected server error                                  | `{ "error": "Internal Server Error" }`                    |

### Examples

```bash
# Health
curl -s localhost:3000/health

# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List / filter
curl -s localhost:3000/books
curl -s 'localhost:3000/books?author=Frank%20Herbert'

# Read one
curl -s localhost:3000/books/1

# Update (full replacement)
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe)","author":"Frank Herbert","year":2019}'

# Delete
curl -s -i -X DELETE localhost:3000/books/1
```

## Project layout

```
src/
  app.ts          Express app factory: routes, validation wiring, error handling
  db.ts           Opens SQLite and creates the schema
  repository.ts   BookRepository: all SQL for the books table
  validation.ts   Zod schemas for bodies, params and query strings
  server.ts       Entrypoint: reads env, starts HTTP server, graceful shutdown
tests/
  books.test.ts        HTTP integration tests (Supertest against an in-memory DB)
  repository.test.ts   Repository unit tests
```
