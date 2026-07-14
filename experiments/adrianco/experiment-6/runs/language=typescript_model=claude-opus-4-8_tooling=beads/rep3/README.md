# Book Collection API

A small REST API for managing a book collection, built with **TypeScript**, **Express**, and **SQLite** (via `better-sqlite3`).

## Requirements

- Node.js 20+ (developed on Node 24)
- npm

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

The server listens on `http://localhost:3000` by default.

Environment variables:

| Variable  | Default     | Description                                              |
| --------- | ----------- | -------------------------------------------------------- |
| `PORT`    | `3000`      | Port to listen on                                        |
| `DB_FILE` | `books.db`  | SQLite file path. Use `:memory:` for an ephemeral store. |

For development with auto-reload:

```bash
npm run dev
```

## Tests

```bash
npm test
```

The suite runs against an in-memory SQLite database, so it leaves no files behind.

## API

All responses are JSON. Request bodies must be JSON (`Content-Type: application/json`).

### `GET /health`

Health check.

```json
{ "status": "ok" }
```

### `POST /books`

Create a book. `title` and `author` are required; `year` (integer) and `isbn` (string) are optional.

```bash
curl -X POST http://localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
```

- `201 Created` — returns the created book (including its `id`)
- `400 Bad Request` — returns `{ "errors": [...] }` when validation fails

### `GET /books`

List all books. Optional `?author=` filter.

```bash
curl http://localhost:3000/books
curl 'http://localhost:3000/books?author=Frank%20Herbert'
```

- `200 OK` — returns an array of books

### `GET /books/{id}`

Fetch a single book by id.

- `200 OK` — returns the book
- `404 Not Found` — no book with that id
- `400 Bad Request` — id is not a positive integer

### `PUT /books/{id}`

Replace a book. Same validation rules as `POST`.

```bash
curl -X PUT http://localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

- `200 OK` — returns the updated book
- `404 Not Found` — no book with that id
- `400 Bad Request` — validation failed or invalid id

### `DELETE /books/{id}`

Delete a book.

- `204 No Content` — deleted
- `404 Not Found` — no book with that id

## Book schema

```ts
{
  id: number;        // assigned by the server
  title: string;     // required
  author: string;    // required
  year: number | null;
  isbn: string | null;
}
```

## Project layout

```
src/
  db.ts          SQLite connection + BookStore data access
  validation.ts  Request-body validation
  app.ts         Express app + routes (DB injected for testability)
  index.ts       Server entrypoint
tests/
  books.test.ts  Integration tests (supertest + in-memory DB)
```
