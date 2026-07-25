# Book Collection API

A REST API for managing a book collection, built with TypeScript, Express 5, and
SQLite via Node's built-in `node:sqlite` module (no native compilation needed).

## Requirements

- Node.js 24+ (uses the built-in `node:sqlite` module; developed on Node 26)
- npm

## Setup

```sh
npm install
```

## Run

```sh
npm run dev        # run directly from TypeScript via tsx
```

or build and run the compiled output:

```sh
npm run build
npm start
```

The server listens on port `3000` by default and stores data in `books.db` in
the working directory. Both are configurable:

```sh
PORT=8080 DB_PATH=/tmp/books.db npm start
```

Use `DB_PATH=:memory:` for an ephemeral in-memory database.

## Test

```sh
npm test
```

Tests run with Vitest + Supertest against an in-memory SQLite database.

## API

| Method | Path          | Description                                | Status codes    |
| ------ | ------------- | ------------------------------------------ | --------------- |
| GET    | `/health`     | Health check                               | 200             |
| POST   | `/books`      | Create a book                              | 201, 400        |
| GET    | `/books`      | List books; supports `?author=` filter     | 200             |
| GET    | `/books/{id}` | Get one book                               | 200, 400, 404   |
| PUT    | `/books/{id}` | Replace a book                             | 200, 400, 404   |
| DELETE | `/books/{id}` | Delete a book                              | 204, 400, 404   |

### Book fields

- `title` (string, **required**, non-empty)
- `author` (string, **required**, non-empty)
- `year` (integer, optional)
- `isbn` (string, optional)

Validation failures return `400` with `{"errors": ["..."]}`. Unknown ids return
`404` with `{"error": "book not found"}`.

### Examples

```sh
# Create
curl -s -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Release It!","author":"Michael Nygard","year":2018,"isbn":"978-1680502398"}'

# List (optionally filtered by author)
curl -s 'localhost:3000/books?author=Michael%20Nygard'

# Get / update / delete
curl -s localhost:3000/books/1
curl -s -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Release It! 2nd Ed","author":"Michael Nygard","year":2018}'
curl -s -X DELETE localhost:3000/books/1 -i
```

## Project layout

```
src/
  app.ts         Express app factory (routes + error handling)
  db.ts          SQLite setup and schema
  validation.ts  Request body validation
  server.ts      Entrypoint
test/
  books.test.ts  Integration tests for all endpoints
```
