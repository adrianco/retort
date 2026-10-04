# Run Summary — rest-api-crud (TypeScript / Express / node:sqlite)

## Surface

A small REST API for a book collection: CRUD over `/books`, an `?author=` list
filter, and a `/health` check. Persistence uses Node's built-in `node:sqlite`
(`DatabaseSync`). HTTP is Express 4 with `express.json()`.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `src/db.ts` | SQLite connection + schema (`books` table), `Book` type | `createDatabase()`, `Book` |
| `src/app.ts` | Express app, validation, all route handlers | `createApp(db)`, `validateBook()` |
| `src/server.ts` | Process entry — opens DB, binds port | top-level `listen` |
| `tests/api.test.ts` | Vitest + supertest integration tests | 4 `it()` cases |

## Interfaces

- `createDatabase(filename?)` → `DatabaseSync`; defaults to `DATABASE_PATH` env or
  `books.sqlite`; tests pass `:memory:`.
- `createApp(db)` → Express `app`; DB injected, so the app is testable without a
  live server. Routes: `GET /health`, `POST /books`, `GET /books`,
  `GET /books/:id`, `PUT /books/:id`, `DELETE /books/:id`.
- `validateBook(body)` → `{value?, error?}`; enforces non-empty string `title`
  and `author`, optional non-negative integer `year`, optional string `isbn`.

## Control flow

`server.ts` → `createDatabase()` → `createApp(db)` → `listen`. Each handler
prepares a statement against the injected `db` and returns JSON. A trailing
error middleware maps malformed JSON bodies to 400 and everything else to 500.

## Notes

- Clean dependency injection of the DB is what makes the tests hermetic
  (`:memory:` per test via `beforeEach`).
- Uses prepared statements throughout — no string-interpolated SQL.
