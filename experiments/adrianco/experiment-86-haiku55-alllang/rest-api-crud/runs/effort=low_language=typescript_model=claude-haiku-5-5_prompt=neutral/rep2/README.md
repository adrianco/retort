# Book Collection API

A REST API for managing a book collection. Built with TypeScript on Node.js,
using the built-in `node:http` server and `node:sqlite` embedded database. It has
no runtime dependencies.

## Requirements

- Node.js 22.13 or newer (Node 22.13+/23.4+ include `node:sqlite`; Node 26 used for development)

## Setup

```bash
npm install
```

## Run

Build and start the server:

```bash
npm run build
npm start
```

Configuration via environment variables:

| Variable  | Default     | Description                          |
|-----------|-------------|--------------------------------------|
| `PORT`    | `3000`      | HTTP port to listen on               |
| `DB_PATH` | `books.db`  | SQLite file path (created if absent) |

Example:

```bash
PORT=8080 DB_PATH=./data/books.db npm start
```

## Test

```bash
npm test
```

This compiles the TypeScript sources and runs the test suite with `node --test`
against an in-memory database.

## API

All request and response bodies are JSON. Errors are returned as
`{ "error": "<message>" }`, with `{ "details": { field: message } }` added for
validation failures.

A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required non-empty strings. `year` (integer 0–3000) and
`isbn` (non-empty string) are optional and may be `null` or omitted.

| Method | Path            | Description                                        | Success |
|--------|-----------------|----------------------------------------------------|---------|
| POST   | `/books`        | Create a book                                      | 201     |
| GET    | `/books`        | List books; optional `?author=` exact-match filter | 200     |
| GET    | `/books/{id}`   | Get one book                                       | 200     |
| PUT    | `/books/{id}`   | Replace a book's fields (full update)              | 200     |
| DELETE | `/books/{id}`   | Delete a book                                      | 204     |
| GET    | `/health`       | Health check                                       | 200     |

Other status codes: `400` invalid input or id, `404` not found or unknown route,
`405` unsupported method, `413` body over 1 MB, `500` unexpected error.

### Examples

```bash
curl -i -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl 'localhost:3000/books?author=Frank%20Herbert'

curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl -i -X DELETE localhost:3000/books/1

curl localhost:3000/health
```

## Project layout

```
src/
  app.ts         HTTP routing and JSON handling
  db.ts          SQLite schema and BookRepository
  validation.ts  Request validation and id parsing
  server.ts      Entry point
test/
  api.test.ts    Integration tests (19 cases)
```
