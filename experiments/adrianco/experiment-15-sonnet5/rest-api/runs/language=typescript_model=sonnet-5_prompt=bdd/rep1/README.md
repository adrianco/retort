# Book Collection API

A REST API for managing a collection of books, built with TypeScript, Express, and SQLite.

## Tech stack

- **Language:** TypeScript
- **Framework:** Express
- **Database:** SQLite via Node's built-in [`node:sqlite`](https://nodejs.org/api/sqlite.html) module (requires Node.js 22.5+, no native build step needed)
- **Testing:** Jest + Supertest

## Requirements

- Node.js >= 22.5.0

## Setup

```bash
npm install
```

## Running the server

Development (runs TypeScript directly):

```bash
npm run dev
```

Production (compiles then runs the JS build):

```bash
npm run build
npm start
```

The server listens on port `3000` by default. Configure with environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_FILE` — path to the SQLite database file (default `books.db`). Use `:memory:` for an ephemeral in-memory database.

## Running tests

```bash
npm test
```

Tests use an in-memory SQLite database, so they don't touch any file on disk.

## API

### `GET /health`

Health check endpoint.

**Response:** `200 OK`

```json
{ "status": "ok" }
```

### `POST /books`

Create a new book. `title` and `author` are required; `year` and `isbn` are optional.

**Request body:**

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

**Responses:**

- `201 Created` — returns the created book, including its generated `id`
- `400 Bad Request` — returns `{ "errors": [...] }` when validation fails

### `GET /books`

List all books. Supports an optional `author` query parameter to filter by exact author match.

```
GET /books
GET /books?author=Frank%20Herbert
```

**Response:** `200 OK` — an array of books (possibly empty)

### `GET /books/:id`

Fetch a single book by ID.

**Responses:**

- `200 OK` — the book
- `404 Not Found` — no book with that ID exists
- `400 Bad Request` — `id` is not a valid integer

### `PUT /books/:id`

Update a book. Accepts a partial body — only the supplied fields are changed. Any supplied `title`/`author` must still be a non-empty string.

**Request body (example, partial update):**

```json
{ "year": 1970 }
```

**Responses:**

- `200 OK` — the updated book
- `404 Not Found` — no book with that ID exists
- `400 Bad Request` — validation failed, or `id` is not a valid integer

### `DELETE /books/:id`

Delete a book.

**Responses:**

- `204 No Content` — deleted successfully
- `404 Not Found` — no book with that ID exists
- `400 Bad Request` — `id` is not a valid integer

## Project structure

```
src/
  app.ts          Express app and route handlers
  db.ts           SQLite database setup/schema
  server.ts       Entry point — creates the DB, app, and starts listening
  types.ts        Shared TypeScript types
  validation.ts   Input validation for book payloads
tests/
  books.test.ts   Integration tests (BDD-style, Given/When/Then)
```
