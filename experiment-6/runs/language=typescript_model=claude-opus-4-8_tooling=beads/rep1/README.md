# Book Collection API

A small REST API for managing a book collection, built with **TypeScript**,
**Express**, and **SQLite** (via `better-sqlite3`).

## Requirements

- Node.js 18+ (developed on Node 24)
- npm

## Setup

```bash
npm install
```

## Run

```bash
npm run build   # compile TypeScript to dist/
npm start       # start the server (default http://localhost:3000)
```

For development with auto-reload:

```bash
npm run dev
```

### Configuration

| Env var   | Default    | Description                  |
| --------- | ---------- | ---------------------------- |
| `PORT`    | `3000`     | Port to listen on            |
| `DB_PATH` | `books.db` | SQLite database file path    |

## Tests

```bash
npm test
```

Tests use an in-memory SQLite database and run the full HTTP stack via
`supertest` — no setup or teardown required.

## API

A book has the shape:

```json
{ "id": 1, "title": "string", "author": "string", "year": 1999, "isbn": "string|null" }
```

`title` and `author` are required. `year` (integer) and `isbn` (string) are
optional.

| Method   | Path           | Description                              | Success |
| -------- | -------------- | ---------------------------------------- | ------- |
| `GET`    | `/health`      | Health check                             | `200`   |
| `POST`   | `/books`       | Create a book                            | `201`   |
| `GET`    | `/books`       | List books (optional `?author=` filter)  | `200`   |
| `GET`    | `/books/{id}`  | Get a single book                        | `200`   |
| `PUT`    | `/books/{id}`  | Update a book                            | `200`   |
| `DELETE` | `/books/{id}`  | Delete a book                            | `204`   |

### Status codes

- `400` — validation failed (missing `title`/`author`, bad `year`/`isbn`, or invalid id)
- `404` — book not found
- `201` / `200` / `204` — success

### Examples

```bash
# Create
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999,"isbn":"978-0201616224"}'

# List all
curl http://localhost:3000/books

# Filter by author
curl 'http://localhost:3000/books?author=Andrew%20Hunt'

# Get one
curl http://localhost:3000/books/1

# Update
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":2019}'

# Delete
curl -X DELETE http://localhost:3000/books/1
```

## Project layout

```
src/
  db.ts      SQLite schema + data-access functions
  book.ts    Request payload validation
  app.ts     Express app factory (db injected for testability)
  server.ts  Entry point
test/
  books.test.ts  Integration tests over the HTTP API
```
