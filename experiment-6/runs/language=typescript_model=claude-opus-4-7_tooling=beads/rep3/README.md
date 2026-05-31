# Book Collection API

A small REST API for managing a book collection. Built with TypeScript, Express, and SQLite (via `better-sqlite3`).

## Requirements

- Node.js 18 or newer (tested on Node 24)
- npm

## Setup

```bash
npm install
npm run build
```

## Run

Development (TypeScript via ts-node, in-memory DB unless `DB_FILE` is set):

```bash
npm run dev
```

Production (compiled JS, persistent SQLite file at `books.sqlite` by default):

```bash
npm start
```

Environment variables:

- `PORT` — listening port (default `3000`)
- `DB_FILE` — SQLite file path (default `books.sqlite`); use `:memory:` for an ephemeral DB

## Test

```bash
npm test
```

The test suite uses an in-memory SQLite DB and exercises every endpoint plus validation paths.

## Endpoints

| Method | Path           | Description                          |
| ------ | -------------- | ------------------------------------ |
| GET    | `/health`      | Health check; returns `{status:"ok"}`|
| POST   | `/books`       | Create a book                        |
| GET    | `/books`       | List books (optional `?author=`)     |
| GET    | `/books/{id}`  | Fetch a single book                  |
| PUT    | `/books/{id}`  | Replace a book                       |
| DELETE | `/books/{id}`  | Delete a book                        |

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

`title` and `author` are required and must be non-empty strings.
`year` is an optional integer. `isbn` is an optional string.

### Example

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'
curl http://localhost:3000/books/1
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"updated"}'
curl -X DELETE http://localhost:3000/books/1
```

### Status codes

- `200 OK` — successful read or update
- `201 Created` — successful create
- `204 No Content` — successful delete
- `400 Bad Request` — invalid body or path parameter
- `404 Not Found` — book id does not exist
- `500 Internal Server Error` — unexpected error

## Project layout

```
src/
  app.ts          Express app factory
  db.ts           SQLite repository
  server.ts       HTTP entry point
  validation.ts   Request body validation
tests/
  books.test.ts   Integration tests (supertest + jest)
```
