# Books API

A small REST service for managing a book collection, written in TypeScript with
[Express 5](https://expressjs.com/) and SQLite via Node's built-in
[`node:sqlite`](https://nodejs.org/api/sqlite.html) module (no native build step).

## Requirements

- Node.js 22.13 or newer (`node:sqlite` is built in; Node 24+ recommended)
- npm

## Setup

```bash
npm install
```

## Run

```bash
# Development (auto-reload via tsx)
npm run dev

# Production
npm run build
npm start
```

The server listens on `http://localhost:3000` by default.

| Environment variable | Default    | Purpose                                            |
| -------------------- | ---------- | -------------------------------------------------- |
| `PORT`               | `3000`     | TCP port to listen on                              |
| `DATABASE_PATH`      | `books.db` | SQLite file path. Use `:memory:` for an ephemeral DB |

The database file and schema are created automatically on first start.

## Test

```bash
npm test         # runs the Vitest suite (integration tests via supertest + unit tests)
npm run typecheck
```

Tests use an in-memory SQLite database, so they leave no files behind.

## API

All request and response bodies are JSON.

| Method   | Path              | Description                                   | Success |
| -------- | ----------------- | --------------------------------------------- | ------- |
| `GET`    | `/health`         | Health check (verifies the database responds) | `200`   |
| `POST`   | `/books`          | Create a book                                 | `201`   |
| `GET`    | `/books`          | List books, optional `?author=` filter        | `200`   |
| `GET`    | `/books/{id}`     | Fetch one book                                | `200`   |
| `PUT`    | `/books/{id}`     | Replace a book                                | `200`   |
| `DELETE` | `/books/{id}`     | Delete a book                                 | `204`   |

### Book payload

```json
{
  "title": "Dune",            // required, non-empty string
  "author": "Frank Herbert",  // required, non-empty string
  "year": 1965,               // optional integer
  "isbn": "9780441013593"     // optional ISBN-10 or ISBN-13 (hyphens allowed)
}
```

Responses add `id`, `created_at` and `updated_at`. Omitted optional fields are
stored and returned as `null`. `PUT` replaces the whole record, so omitted
optional fields become `null`.

The `?author=` filter is an exact, case-insensitive match.

### Error responses

| Status | When                                                        |
| ------ | ----------------------------------------------------------- |
| `400`  | Validation failure, malformed JSON, or non-numeric `{id}`   |
| `404`  | Unknown book id or unknown route                            |
| `413`  | Request body larger than 100 KB                             |
| `503`  | `/health` when the database does not respond               |

Validation errors list each failing field:

```json
{
  "error": "Validation failed",
  "details": [
    { "field": "title", "message": "title is required" },
    { "field": "author", "message": "author is required" }
  ]
}
```

### Examples

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'http://localhost:3000/books?author=Frank%20Herbert'
curl http://localhost:3000/books/1

curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -X DELETE http://localhost:3000/books/1
curl http://localhost:3000/health
```

## Project layout

```
src/
  server.ts       entry point: wires the DB, app and graceful shutdown
  app.ts          Express app and route handlers
  db.ts           BookRepository: schema and SQL access via node:sqlite
  validation.ts   payload and id validation
  types.ts        shared types
tests/
  books.test.ts        HTTP integration tests (supertest, in-memory SQLite)
  validation.test.ts   unit tests for the validators
```
