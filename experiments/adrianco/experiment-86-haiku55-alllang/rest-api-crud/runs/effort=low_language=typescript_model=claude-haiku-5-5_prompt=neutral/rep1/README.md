# Book Collection API

A REST API for managing a book collection. Built with TypeScript on Node.js's
built-in `http` module, with data stored in SQLite via the built-in `node:sqlite`
module. No native addons or runtime dependencies.

## Requirements

- Node.js **22.13 or later** (`node:sqlite` is available unflagged from 22.13 / 23.4+)
- npm

## Setup

```bash
npm install
```

## Run

```bash
npm run build      # compile TypeScript to dist/
npm start          # start the server on port 3000
```

Or in one step: `npm run dev`.

Environment variables:

| Variable        | Default     | Description                              |
|-----------------|-------------|------------------------------------------|
| `PORT`          | `3000`      | HTTP port to listen on                   |
| `DATABASE_PATH` | `books.db`  | SQLite file path (created if missing)    |

## Test

```bash
npm test
```

Tests use `node:test` and run against an in-memory SQLite database on a random port.

## API

Book fields: `id` (integer, server-assigned), `title` (required), `author` (required),
`year` (optional integer, 1450 to next year), `isbn` (optional ISBN-10/13 string).

| Method | Path          | Description                                   | Success |
|--------|---------------|-----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                 | 201     |
| GET    | `/books`      | List books; optional `?author=` filter (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                  | 200     |
| PUT    | `/books/{id}` | Update a book (any subset of fields)          | 200     |
| DELETE | `/books/{id}` | Delete a book                                 | 204     |
| GET    | `/health`     | Health check (verifies database reachable)    | 200     |

Errors return JSON `{ "error": "<message>" }`, with a `details` object for validation
failures (field name → message). Status codes: `400` validation/malformed input,
`404` not found, `405` method not allowed, `413` body over 1 MB, `500` server error.

### Examples

```bash
curl -i -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:3000/books?author=Frank%20Herbert
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' -d '{"year":1966}'
curl -X DELETE localhost:3000/books/1
curl localhost:3000/health
```
