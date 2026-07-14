# Book Collection API

A REST API for managing a collection of books, built with TypeScript, Express, and SQLite.

## Requirements

- Node.js 22.5+ (uses the built-in `node:sqlite` module — no native build/compilation required)

## Setup

```bash
npm install
```

## Run

Development (runs TypeScript directly via ts-node):

```bash
npm run dev
```

Production (compile then run):

```bash
npm run build
npm start
```

The server listens on port `3000` by default. Configure with environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_FILE` — path to the SQLite database file (default `books.db`, created automatically)

## Test

```bash
npm test
```

Tests run against an in-memory SQLite database (`:memory:`), so they don't touch the on-disk database file.

## API

### `GET /health`

Health check. Returns `200 OK`:

```json
{ "status": "ok" }
```

### `POST /books`

Create a book. `title` and `author` are required.

Request body:

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

- `201 Created` with the created book (including its `id`) on success.
- `400 Bad Request` with `{ "errors": [...] }` if `title` or `author` is missing/invalid.

### `GET /books`

List all books. Supports an optional `author` query parameter to filter:

```
GET /books?author=Frank%20Herbert
```

Returns `200 OK` with an array of books.

### `GET /books/:id`

Fetch a single book by ID.

- `200 OK` with the book.
- `404 Not Found` if no book exists with that ID.

### `PUT /books/:id`

Update a book. Accepts a partial body — any of `title`, `author`, `year`, `isbn`. Fields omitted from the body are left unchanged.

- `200 OK` with the updated book.
- `400 Bad Request` if a provided field fails validation.
- `404 Not Found` if no book exists with that ID.

### `DELETE /books/:id`

Delete a book.

- `204 No Content` on success.
- `404 Not Found` if no book exists with that ID.

## Project structure

```
src/
  db.ts          # SQLite connection + schema setup
  validation.ts  # Request body validation
  app.ts         # Express app and routes
  types.ts       # Shared TypeScript types
  index.ts       # Entry point — wires up the DB and starts the server
tests/
  books.test.ts  # Integration tests (Jest + Supertest)
```
