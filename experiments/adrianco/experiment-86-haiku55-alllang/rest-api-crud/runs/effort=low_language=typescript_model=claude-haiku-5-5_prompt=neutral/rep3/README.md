# Book API

A REST API for managing a book collection. Built with TypeScript on Node's built-in `http` module, with data stored in embedded SQLite via the built-in `node:sqlite` module. It has no runtime dependencies.

## Requirements

- Node.js 22.13 or newer (Node 22.13+ and 23.4+ ship `node:sqlite` without a flag; Node 26 is what this was tested on)
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

Or build and start in one step with `npm run dev`.

Environment variables:

| Variable        | Default           | Description                                |
|-----------------|-------------------|--------------------------------------------|
| `PORT`          | `3000`            | HTTP port to listen on                     |
| `DATABASE_PATH` | `data/books.db`   | SQLite file path (`:memory:` for in-memory)|

## Test

```bash
npm test
```

This compiles the project and runs the test suite with `node --test`. The tests start the HTTP server on a random port against an in-memory database.

## API

All request and response bodies are JSON.

A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required non-empty strings. `year` (integer) and `isbn` (string) are optional and may be `null`.

| Method | Path          | Description                              | Success | Errors               |
|--------|---------------|------------------------------------------|---------|----------------------|
| POST   | `/books`      | Create a book                            | 201     | 400                  |
| GET    | `/books`      | List books; optional `?author=` filter (exact match) | 200 | |
| GET    | `/books/{id}` | Get a book by ID                         | 200     | 404                  |
| PUT    | `/books/{id}` | Replace a book's fields                  | 200     | 400, 404             |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 404                  |
| GET    | `/health`     | Health check, includes database status   | 200     |                      |

Validation failures return `400` with a `details` object keyed by field name. Malformed JSON returns `400`. Unknown routes return `404`, and unsupported methods on a known route return `405`. Request bodies over 1 MB return `413`.

### Examples

```bash
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl "localhost:3000/books?author=Frank%20Herbert"
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:3000/books/1
curl localhost:3000/health
```

## Project layout

```
src/
  server.ts      entry point: reads env, opens DB, starts listening
  app.ts         HTTP routing and JSON responses
  db.ts          BookRepository, SQLite access
  validation.ts  request body validation
test/
  books.test.ts  integration tests (HTTP against in-memory DB)
```
