# Architecture Summary

REST API for a book collection, TypeScript + Express + better-sqlite3.

## Modules

- **`src/server.ts`** — Express `app` with all routes. Exports the app (no `listen`)
  so tests can bind an ephemeral port. Routes: `GET /health`, `POST /books`,
  `GET /books` (with `?author=` filter), `GET /books/:id`, `PUT /books/:id`,
  `DELETE /books/:id`. Uses prepared statements from the shared `db`.
- **`src/database.ts`** — opens a `better-sqlite3` database at `./data/books.db`
  (creating the `data/` dir if absent) and runs a `CREATE TABLE IF NOT EXISTS books`
  DDL with `title`/`author` NOT NULL, `year` INTEGER, `isbn` TEXT.
- **`src/index.ts`** — entry point; imports `app` and calls `listen(PORT)`.
- **`tests/api.test.ts`** — supertest integration tests over the exported app
  (health, create+get, list+filter, update, delete).

## Flow

`index.ts` → `server.ts` (routes) → `database.ts` (persistence). Validation
(`title` and `author` required) is enforced inline in the POST and PUT handlers,
returning 400. Status codes: 201 create, 200 read/update, 204 delete, 404 not
found, 400 validation.

## Notes

- Persistence is on-disk SQLite (satisfies R7), not in-memory.
- Tests share the same persistent `data/books.db` with no per-test reset; state
  accumulates across runs but the assertions use `arrayContaining`/`objectContaining`
  so they remain robust.
