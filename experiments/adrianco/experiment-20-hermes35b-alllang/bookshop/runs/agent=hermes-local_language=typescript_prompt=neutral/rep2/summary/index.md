# Architecture Summary — bookshop (TypeScript / Express / better-sqlite3)

Small, layered Express REST service. ~5 source modules, clean separation of concerns.

## Modules

| File | Role |
|------|------|
| `server.ts` | Entry point. Binds `app` to `PORT` (default 3000), wires SIGINT/SIGTERM graceful shutdown that closes the DB. |
| `app.ts` | Builds the Express `app`: JSON body middleware, mounts `/books` router, `GET /health`, a 404 fallthrough, and a 500 error handler. Exported (not listening) so tests can drive it via supertest. |
| `routes.ts` | `Router` for the five CRUD endpoints under `/books`. Handles request parsing, ID validation (`parseInt`/`isNaN`), required-field validation, and status codes (201/200/204/400/404). |
| `db.ts` | Data layer over `better-sqlite3`. Lazy singleton connection (`:memory:` default), `books` table DDL, and typed CRUD helpers (`getAllBooks`, `getBookById`, `createBook`, `updateBook`, `deleteBook`). Exports the `Book` type. `initializeDatabase(path)` allows re-pointing the connection (used by tests to reset). |
| `tests.spec.ts` | 16 supertest integration tests across health, POST, GET (list/filter/by-id), PUT, DELETE, and persistence. `beforeEach` resets an in-memory DB. |

## Request flow

`server.ts → app.ts (express.json → /books router | /health | 404 | error) → routes.ts (validate → db.ts helper → prepared statement → JSON response)`

## Interfaces

- `Book = { id, title, author, year|null, isbn|null }`
- Router-level parsing/validation is separate from persistence; the db layer is framework-agnostic and directly unit-testable.

## Notes

- DB connection is a module-level singleton in `:memory:` mode — good for tests, but the running server does not persist data across restarts.
- Tests target compiled `dist/tests.spec.js` (jest `testMatch`), so a successful `tsc` build is a precondition for the test run.
