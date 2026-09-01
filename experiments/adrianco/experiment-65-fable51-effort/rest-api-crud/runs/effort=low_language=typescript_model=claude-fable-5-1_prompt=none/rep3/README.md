# Books API

A small REST service for managing a book collection, built with TypeScript, Express, and
SQLite via Node's built-in `node:sqlite` module (no native compilation required).

## Requirements

- Node.js 22.13 or newer (tested on Node 26). `node:sqlite` ships with Node, so there are no
  native dependencies.

## Setup

```bash
npm install
```

## Run

```bash
npm run build     # compile TypeScript to dist/
npm start         # start on http://localhost:3000
```

For development without a build step:

```bash
npm run dev
```

Environment variables:

| Variable  | Default    | Description                                   |
|-----------|------------|-----------------------------------------------|
| `PORT`    | `3000`     | TCP port to listen on                          |
| `DB_PATH` | `books.db` | SQLite file path. Use `:memory:` for ephemeral |

## Test

```bash
npm test
```

Tests use an in-memory SQLite database and exercise every endpoint through supertest.

## API

| Method | Path                  | Description                                  | Success |
|--------|-----------------------|----------------------------------------------|---------|
| GET    | `/health`             | Health check                                 | 200     |
| POST   | `/books`              | Create a book                                | 201     |
| GET    | `/books`              | List books, optional `?author=` exact filter | 200     |
| GET    | `/books/{id}`         | Get one book                                 | 200     |
| PUT    | `/books/{id}`         | Replace a book                               | 200     |
| DELETE | `/books/{id}`         | Delete a book                                | 204     |

Book shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required non-empty strings. `year` is an optional integer
(0 to 9999) and `isbn` is an optional string. Validation failures return `400` with an
`error` and a `details` array. Unknown ids return `404`. Malformed JSON returns `400`.

Example:

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:3000/books?author=Frank%20Herbert'
```

## Layout

- `src/db.ts` — SQLite repository
- `src/validation.ts` — input validation
- `src/app.ts` — Express app and routes
- `src/server.ts` — entry point
- `tests/books.test.ts` — integration tests
