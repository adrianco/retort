# Book Collection API

A small REST API for managing a book collection, built with TypeScript, Express,
and SQLite (via `better-sqlite3`).

## Requirements

- Node.js 18+ (tested on Node 24)
- npm

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

Or run in dev mode (no build step):

```bash
npm run dev
```

The server listens on `http://localhost:3000` by default. Override with
environment variables:

- `PORT` — port to listen on (default `3000`)
- `DB_PATH` — SQLite file path (default `books.db`)

## Tests

```bash
npm test
```

Tests run against an in-memory SQLite database, so no filesystem state is
touched.

## Endpoints

| Method | Path           | Description                                  |
| ------ | -------------- | -------------------------------------------- |
| GET    | `/health`      | Health check (`{ "status": "ok" }`)          |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List books, optional `?author=` filter       |
| GET    | `/books/:id`   | Get a single book                            |
| PUT    | `/books/:id`   | Replace a book                               |
| DELETE | `/books/:id`   | Delete a book                                |

### Book schema

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0547928227"
}
```

`title` and `author` are required (non-empty strings). `year` (integer) and
`isbn` (string) are optional.

### Example

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937}'

# List by author
curl 'http://localhost:3000/books?author=J.R.R.%20Tolkien'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit (Revised)","author":"J.R.R. Tolkien","year":1951}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Status codes

- `200` — successful GET / PUT
- `201` — successful POST
- `204` — successful DELETE
- `400` — invalid input or invalid id
- `404` — book not found
- `500` — internal error
