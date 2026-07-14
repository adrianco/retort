# Architecture Summary

> `run-summary` skill was not available in this session; this is a concise hand-written summary.

## Modules

| File | LOC | Responsibility |
|------|-----|----------------|
| `src/database.ts` | 168 | SQLite data-access layer. `Database` class wrapping `sqlite3` with promisified `all`/`get`/`run` helpers and typed `Book` CRUD methods. |
| `src/app.ts` | 175 | Express application: route handlers for all 6 endpoints + `/health`, JSON body parsing, input validation, error-handling middleware, graceful shutdown. |
| `tests/integration.test.ts` | 238 | Supertest integration suite (17 tests) exercising every endpoint incl. validation, 404, 409, and filter paths. |

## Interfaces

- `Book { id, title, author, year, isbn }` — shared domain type exported from `database.ts`.
- `Database` methods: `createBook`, `getAllBooks(author?)`, `getBookById`, `updateBook`, `deleteBook`, `clearAllBooks` (test isolation), `close`.
- `app` and `db` are exported from `app.ts` for in-process testing; server only binds a port when run as the main module.

## Flow

HTTP request → `express.json()` → route handler (validate → call `db.*`) → JSON response with status code. DB errors surface via `next(error)` to a 500 handler; `UNIQUE constraint failed` is caught and mapped to 409. Persistence is SQLite on disk (`DB_PATH`, default `books.db`); tests inject `:memory:`.
