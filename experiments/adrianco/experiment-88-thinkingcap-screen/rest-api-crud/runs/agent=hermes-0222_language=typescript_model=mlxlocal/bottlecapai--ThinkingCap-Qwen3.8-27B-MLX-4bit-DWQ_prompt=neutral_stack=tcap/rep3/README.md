# Book API

A REST API service for managing a book collection, built with **TypeScript**,
**Express**, and **SQLite** (Node's built-in `node:sqlite` module — no native
database driver required).

## Requirements

- Node.js **>= 22.5** (uses the built-in `node:sqlite` module)

## Setup

```bash
npm install
```

## Run

Production-style (compile then run):

```bash
npm run build
npm start
```

Development (no build step, via tsx):

```bash
npm run dev
```

The server listens on port **8000** by default.

### Environment variables

| Variable        | Default            | Description                          |
| --------------- | ------------------ | ------------------------------------ |
| `PORT`          | `8000`             | Port to listen on                    |
| `DATABASE_PATH` | `./books.db`       | Path to the SQLite database file     |

Example:

```bash
PORT=3000 DATABASE_PATH=/tmp/books.db npm start
```

## Tests

```bash
npm test
```

Runs the vitest suite (integration tests against the Express app with an
in-memory SQLite database, plus unit tests for the validation layer).

## Endpoints

### `GET /`

Service info (name, status, endpoint list).

### `GET /health`

Health check.

```
200 { "status": "ok", "uptime": 12.34 }
```

### `POST /books`

Create a book. `title` and `author` are required; `year` and `isbn` are
optional.

```bash
curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-261-10235-9"}'
```

```
201 { "id": 1, "title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0-261-10235-9" }
```

### `GET /books`

List all books. Supports an optional `?author=` filter (case-insensitive
exact match).

```bash
curl 'http://localhost:8000/books?author=Tolkien'
```

```
200 [ { "id": 1, "title": "The Hobbit", ... } ]
```

### `GET /books/{id}`

Get a single book by ID.

```
200 { "id": 1, ... }
404 { "error": "book 42 not found" }
400 { "error": "id must be a positive integer" }
```

### `PUT /books/{id}`

Update a book. Partial updates: only the fields present in the body are
changed; the rest are preserved. Sending `null` for `year` or `isbn` clears
it.

```bash
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"year": 1938}'
```

```
200 { "id": 1, ... "year": 1938 }
404 { "error": "book 42 not found" }
400 { "error": "..." }
```

### `DELETE /books/{id}`

Delete a book.

```
204 (no body)
404 { "error": "book 42 not found" }
```

## Validation rules

- `title`: required, non-empty string, max 500 chars (trimmed).
- `author`: required, non-empty string, max 200 chars (trimmed).
- `year`: optional, integer between 1000 and 2100.
- `isbn`: optional, must be a valid ISBN-10 or ISBN-13 (hyphens/spaces
  allowed, e.g. `978-0-261-10235-9` or `0-8044-2957-X`).
- Malformed JSON bodies and unknown routes return `400` / `404` JSON errors.

## Project layout

```
src/
  app.ts         Express app factory (routes, error handling)
  db.ts          SQLite schema + CRUD layer (node:sqlite)
  validation.ts  Input validation rules
  server.ts      Entry point (reads PORT / DATABASE_PATH)
tests/
  books.test.ts      Integration tests (supertest + in-memory SQLite)
  validation.test.ts Unit tests for the validation layer
```
