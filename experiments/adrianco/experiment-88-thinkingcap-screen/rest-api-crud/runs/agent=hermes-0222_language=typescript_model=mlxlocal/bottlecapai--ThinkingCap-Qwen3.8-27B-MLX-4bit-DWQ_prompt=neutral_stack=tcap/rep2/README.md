# Book API

A REST API service for managing a book collection, built with **TypeScript**,
**Express**, and **SQLite** (via `better-sqlite3`).

## Requirements

- Node.js >= 20
- npm

## Setup

```bash
npm install
```

## Run

```bash
npm run build
npm start
```

The server listens on port `8000` by default. Configure with environment
variables:

- `PORT` — port to listen on (default `8000`)
- `DB_PATH` — path to the SQLite file (default `books.db`). Use `:memory:` for
  an in-memory database.

Example:

```bash
PORT=8080 DB_PATH=./data/books.db npm start
```

## Tests

```bash
npm test
```

This compiles the TypeScript and runs the integration test suite (Node's built-in
test runner + supertest) against an in-memory SQLite database.

## Endpoints

| Method | Path             | Description                          | Success | Errors          |
| ------ | ---------------- | ------------------------------------ | ------- | --------------- |
| GET    | `/health`        | Health check                         | 200     | —               |
| POST   | `/books`         | Create a book                        | 201     | 400             |
| GET    | `/books`         | List all books (`?author=` filter)   | 200     | —               |
| GET    | `/books/{id}`    | Get a single book                    | 200     | 400, 404        |
| PUT    | `/books/{id}`    | Update a book (partial update)       | 200     | 400, 404        |
| DELETE | `/books/{id}`    | Delete a book                        | 204     | 400, 404        |

### Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required; `year` (integer) and `isbn` (string) are
optional and may be `null`.

### Validation

- `POST /books`: `title` and `author` are required non-empty strings.
- `PUT /books/{id}`: only the provided fields are updated; each provided field
  is validated, and at least one field must be provided.
- Invalid input returns `400` with `{ "error": "Validation failed", "details": [...] }`.
- Malformed JSON bodies return `400`.
- Unknown routes return a JSON `404`.

### Example requests

```bash
# Create
curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List (optionally filter by author, case-insensitive)
curl 'http://localhost:8000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:8000/books/1

# Update
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year":1966}'

# Delete
curl -X DELETE http://localhost:8000/books/1
```

## Project layout

```
src/
  server.ts    — entry point (reads PORT / DB_PATH, starts listening)
  app.ts       — Express app factory (health check, error handlers)
  books.ts     — /books route handlers
  db.ts        — SQLite open + schema initialization
  validate.ts  — input validation helpers
tests/
  books.test.ts — integration tests (node:test + supertest)
```
