# Books API

A small REST service for managing a book collection, written in TypeScript with
Express 5 and backed by SQLite.

Persistence uses Node's built-in [`node:sqlite`](https://nodejs.org/api/sqlite.html)
module, so there is no native compilation step and no external database to run.

## Requirements

- Node.js **22.5 or newer** (`node:sqlite` is unavailable before that; developed on Node 26)
- npm

## Setup

```bash
npm install
```

## Run

```bash
npm run dev     # watch mode via tsx, reloads on change
```

or build and run the compiled output:

```bash
npm run build
npm start
```

The server listens on <http://localhost:3000> and writes to `books.db` in the
working directory. Both are configurable:

| Variable        | Default    | Purpose                                  |
| --------------- | ---------- | ---------------------------------------- |
| `PORT`          | `3000`     | TCP port to listen on                    |
| `DATABASE_FILE` | `books.db` | SQLite file; use `:memory:` for ephemeral |

```bash
PORT=8080 DATABASE_FILE=/var/data/books.db npm start
```

## Test

```bash
npm test          # vitest, 33 tests
npm run typecheck # tsc --noEmit
```

Tests run against the real Express app and a real SQLite database (in-memory,
fresh per test) driven through HTTP with supertest — no mocking of the store.

## API

All responses are JSON, except `204 No Content` which has an empty body.

### `GET /health`

Liveness check. Runs a query against SQLite, so it reflects real database state.

```json
{ "status": "ok", "database": "ok" }
```

Returns `503` with `{"status":"error","database":"unavailable"}` if the database
cannot be reached.

### `POST /books`

Creates a book. Responds `201` with the created book and a `Location` header.

| Field    | Type             | Required | Notes                                     |
| -------- | ---------------- | -------- | ----------------------------------------- |
| `title`  | string           | yes      | Non-empty after trimming, ≤ 512 chars      |
| `author` | string           | yes      | Non-empty after trimming, ≤ 512 chars      |
| `year`   | integer or null  | no       | −3000 … 9999; defaults to `null`           |
| `isbn`   | string or null   | no       | ISBN-10 or ISBN-13, hyphens/spaces allowed; must be unique |

```bash
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

### `GET /books`

Lists all books, oldest first. Supports an optional `?author=` filter, which is
an exact, case-insensitive match (not a substring search).

```bash
curl 'localhost:3000/books?author=frank%20herbert'
```

### `GET /books/{id}`

Returns one book, or `404` if the id is unknown.

### `PUT /books/{id}`

Replaces a book. The body takes the same shape and validation rules as `POST`.
Because this is a full replacement, **omitting `year` or `isbn` clears them** —
send the complete representation you want stored.

### `DELETE /books/{id}`

Removes a book. Responds `204` on success, `404` if the id is unknown.

## Status codes

| Code  | When                                                                |
| ----- | ------------------------------------------------------------------- |
| `200` | Successful `GET` or `PUT`                                            |
| `201` | Book created                                                         |
| `204` | Book deleted                                                         |
| `400` | Validation failure, malformed JSON, or a non-numeric `id`             |
| `404` | No book with that id, or unknown route                               |
| `409` | The `isbn` is already used by another book                           |
| `413` | Request body over 100 kB                                             |
| `500` | Unexpected server error                                              |
| `503` | Health check could not reach the database                            |

Errors use a consistent envelope. Validation failures list every offending
field at once rather than stopping at the first:

```json
{
  "error": "validation failed",
  "details": [
    { "field": "title", "message": "title is required" },
    { "field": "year", "message": "year must be an integer" }
  ]
}
```

## Layout

```
src/
  server.ts      entry point — config, listen, graceful shutdown
  app.ts         Express app factory: routes, error envelope
  db.ts          BookStore — SQLite schema and queries
  validation.ts  request-body validation, id parsing
  types.ts       shared interfaces
tests/
  books.test.ts  HTTP-level integration tests for every endpoint
  store.test.ts  BookStore unit tests (on-disk persistence, constraints)
```

`createApp(store)` takes the store as an argument rather than reaching for a
global, which is what lets the tests hand it a throwaway in-memory database.

## Design notes

- **SQL injection** is prevented by binding every value as a parameter. The
  `?author=` filter uses `= ? COLLATE NOCASE` rather than `LIKE`, so a value
  like `%` matches a literal percent sign instead of every row.
- **`isbn` is `UNIQUE`.** SQLite treats `NULL`s as distinct, so any number of
  books may have no ISBN, while a real duplicate is rejected with `409`.
- **Ids are validated before the query.** A path like `/books/abc` returns `400`
  rather than being coerced to `NaN` and silently 404-ing.
- **Writes are synchronous.** `node:sqlite` is a synchronous API and this is a
  single-node embedded store, so there is no connection pool to manage. For
  higher write concurrency the store is the seam to swap out.
