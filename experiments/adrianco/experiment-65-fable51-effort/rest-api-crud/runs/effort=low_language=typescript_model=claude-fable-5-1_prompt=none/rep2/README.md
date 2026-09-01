# Books API

A small REST API for managing a book collection, built with TypeScript, Express 5 and SQLite (via `better-sqlite3`).

## Requirements

- Node.js 20 or newer
- npm

## Setup

```bash
npm install
```

## Run

Development (no build step, auto-reloads via `tsx`):

```bash
npm run dev
```

Production:

```bash
npm run build
npm start
```

The server listens on `http://localhost:3000` by default and stores data in `books.db` in the working directory.

| Variable  | Default    | Description                       |
|-----------|------------|-----------------------------------|
| `PORT`    | `3000`     | HTTP port                         |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` ok)  |

## Test

```bash
npm test
```

Tests run against an in-memory SQLite database using Vitest and Supertest.

## API

All responses are JSON. Validation and lookup errors return `{ "errors": [ "..." ] }`.

| Method   | Path                    | Description                                  | Success |
|----------|-------------------------|----------------------------------------------|---------|
| `GET`    | `/health`               | Health check                                 | `200`   |
| `POST`   | `/books`                | Create a book                                | `201`   |
| `GET`    | `/books`                | List books, optional `?author=` filter       | `200`   |
| `GET`    | `/books/{id}`           | Get one book                                 | `200`   |
| `PUT`    | `/books/{id}`           | Replace a book (full update)                 | `200`   |
| `DELETE` | `/books/{id}`           | Delete a book                                | `204`   |

Book shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

Validation rules:

- `title` and `author` are required, non-empty strings.
- `year` is optional; if present it must be an integer between 0 and five years from now.
- `isbn` is optional; if present it must be a valid ISBN-10 or ISBN-13 (hyphens and spaces allowed).

Status codes: `400` for invalid input or malformed JSON, `404` for unknown book or route.

### Examples

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl 'localhost:3000/books?author=Frank%20Herbert'
curl localhost:3000/books/1
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:3000/books/1
```

## Project layout

```
src/app.ts         Express app and routes
src/db.ts          SQLite connection and schema
src/validation.ts  Input validation helpers
src/server.ts      Entry point
tests/             Vitest + Supertest integration tests
```
