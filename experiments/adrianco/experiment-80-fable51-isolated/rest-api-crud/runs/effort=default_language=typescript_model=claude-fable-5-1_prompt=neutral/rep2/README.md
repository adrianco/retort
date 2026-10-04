# Books API

A small REST service for managing a book collection, written in TypeScript.
It uses only the Node.js standard library at runtime: `node:http` for the server
and `node:sqlite` for embedded SQLite storage.

## Requirements

- Node.js 22.13 or newer (for the built-in `node:sqlite` module)

## Setup

```bash
npm install
npm run build
```

## Run

```bash
npm start
```

| Variable  | Default    | Purpose                                         |
|-----------|------------|-------------------------------------------------|
| `PORT`    | `3000`     | Port to listen on                               |
| `DB_PATH` | `books.db` | SQLite file (`:memory:` for a throwaway store)  |

## Test

```bash
npm test
```

This compiles the project and runs the integration tests with the built-in
Node test runner. Each test starts the server on a random port with an in-memory database.

## API

A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required non-empty strings. `year` (integer) and `isbn`
(string) are optional and stored as `null` when omitted.

| Method | Path          | Description                                  | Success | Errors        |
|--------|---------------|----------------------------------------------|---------|---------------|
| GET    | `/health`     | Health check                                 | 200     |               |
| POST   | `/books`      | Create a book                                | 201     | 400           |
| GET    | `/books`      | List books; `?author=` filters by exact author (case-insensitive) | 200 | |
| GET    | `/books/{id}` | Get one book                                 | 200     | 400, 404      |
| PUT    | `/books/{id}` | Replace a book (full body, same validation as create) | 200 | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                                | 204     | 400, 404      |

Errors are JSON: `{ "error": "validation failed", "details": ["title is required ..."] }`.
Unknown paths return 404, unsupported methods 405, and bodies over 1 MB 413.

### Example

```bash
curl -X POST localhost:3000/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:3000/books?author=Frank%20Herbert'
curl -X PUT localhost:3000/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:3000/books/1
```

## Layout

- `src/validation.ts` — request body validation
- `src/store.ts` — SQLite-backed `BookStore`
- `src/app.ts` — HTTP routing and handlers
- `src/server.ts` — entry point
- `tests/books.test.ts` — integration tests
