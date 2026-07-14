# Book Collection API

A small REST API for managing a book collection, built with **TypeScript**,
**Express 5**, and **SQLite** (via `better-sqlite3`).

## Requirements

- Node.js **22+** (developed/tested on Node 24). Native TypeScript execution is
  used, so no build step is required to run the server.

## Setup

```bash
npm install
```

## Run

Run directly from TypeScript source (no build needed):

```bash
npm run dev      # starts with --watch on http://localhost:3000
```

Or compile to JavaScript and run the build:

```bash
npm run build
npm start
```

### Configuration

| Env var   | Default    | Description                                              |
| --------- | ---------- | -------------------------------------------------------- |
| `PORT`    | `3000`     | Port to listen on                                        |
| `DB_PATH` | `books.db` | SQLite file path. Use `:memory:` for an ephemeral store. |

## API

All responses are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": null }
```

`title` and `author` are required; `year` (integer) and `isbn` (string) are optional.

| Method   | Path             | Description                          | Success status |
| -------- | ---------------- | ------------------------------------ | -------------- |
| `GET`    | `/health`        | Health check                         | `200`          |
| `POST`   | `/books`         | Create a book                        | `201`          |
| `GET`    | `/books`         | List books (optional `?author=` filter) | `200`      |
| `GET`    | `/books/:id`     | Get a single book                    | `200`          |
| `PUT`    | `/books/:id`     | Update a book                        | `200`          |
| `DELETE` | `/books/:id`     | Delete a book                        | `204`          |

### Status codes

- `400` — validation failed (e.g. missing `title`/`author`, non-integer `id`).
  The body contains `{ "errors": [...] }`.
- `404` — book not found.

### Examples

```bash
# Create
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all / filter by author
curl localhost:3000/books
curl 'localhost:3000/books?author=Frank%20Herbert'

# Get one
curl localhost:3000/books/1

# Update
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE localhost:3000/books/1
```

## Tests

Integration tests run against the app on an in-memory SQLite database using
Node's built-in test runner:

```bash
npm test
```

## Project structure

```
src/
  db.ts          # SQLite connection + schema
  app.ts         # Express app, routes, and validation
  server.ts      # Entry point (starts the HTTP server)
  app.test.ts    # Integration tests
```
