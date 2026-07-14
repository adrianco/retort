# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express, and SQLite (via Node's built-in `node:sqlite` module).

## Requirements

- Node.js 22.5+ (uses the built-in `node:sqlite` module, no native build step required)

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

By default the server listens on port `3000` and stores data in `books.db` in the working directory. Both are configurable via environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_PATH` — path to the SQLite database file (default `books.db`, use `:memory:` for an ephemeral database)

## Test

```bash
npm test
```

## API

### `GET /health`

Health check. Returns `200 { "status": "ok" }`.

### `POST /books`

Create a book. Body:

```json
{ "title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0261102217" }
```

- `title` and `author` are required; `year` and `isbn` are optional.
- Returns `201` with the created book, or `400 { "error": "..." }` if `title` or `author` is missing.

### `GET /books`

List all books. Supports an optional `?author=` query parameter to filter by exact author match. Returns `200` with an array of books.

### `GET /books/{id}`

Get a single book by ID. Returns `200` with the book, or `404 { "error": "..." }` if not found.

### `PUT /books/{id}`

Update a book. Body is the same shape as `POST /books`. Returns `200` with the updated book, `400` if `title` or `author` is missing, or `404` if the book does not exist.

### `DELETE /books/{id}`

Delete a book. Returns `204` with no body on success, or `404` if the book does not exist.

## Project structure

- `src/db.ts` — SQLite connection and schema setup
- `src/app.ts` — Express app and route handlers
- `src/server.ts` — process entry point
- `tests/` — Jest + Supertest integration tests
