# Book Collection API

A small REST API for managing a book collection, built with **TypeScript**,
**Express**, and **SQLite** (via `better-sqlite3`).

## Features

- Full CRUD for books (`title`, `author`, `year`, `isbn`)
- List filtering by author (`GET /books?author=...`)
- Input validation (`title` and `author` required)
- JSON responses with appropriate HTTP status codes
- Health check endpoint
- Integration tests with Jest + Supertest

## Requirements

- Node.js 18+ (developed/tested on Node 24)
- npm

## Setup

```bash
npm install
```

## Run

```bash
# Build TypeScript, then start the server
npm run build
npm start

# …or run directly with ts-node (no build step)
npm run dev
```

The server listens on `http://localhost:3000` by default. Configure via
environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_FILE` — SQLite file path (default `books.db`)

## Test

```bash
npm test
```

Tests use an in-memory SQLite database, so they do not touch your data file.

## API

| Method | Path           | Description                          | Success |
| ------ | -------------- | ------------------------------------ | ------- |
| GET    | `/health`      | Health check                         | 200     |
| POST   | `/books`       | Create a book                        | 201     |
| GET    | `/books`       | List books (optional `?author=`)     | 200     |
| GET    | `/books/:id`   | Get a single book                    | 200     |
| PUT    | `/books/:id`   | Update a book                        | 200     |
| DELETE | `/books/:id`   | Delete a book                        | 204     |

### Book object

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are
optional and default to `null`.

### Error responses

| Status | When                                            | Body                                  |
| ------ | ----------------------------------------------- | ------------------------------------- |
| 400    | Validation failed                               | `{ "errors": ["title is required…"] }`|
| 400    | Malformed JSON / bad id                          | `{ "error": "…" }`                    |
| 404    | Book not found                                  | `{ "error": "Book not found" }`       |

## Example requests

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List (all)
curl http://localhost:3000/books

# List (filter by author)
curl 'http://localhost:3000/books?author=Frank%20Herbert'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
src/
  index.ts        # Server entrypoint
  app.ts          # Express app + routes
  db.ts           # SQLite data access layer
  validation.ts   # Request body validation
test/
  books.test.ts   # Integration tests
```
