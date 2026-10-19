# Architecture Summary

TypeScript / Express 5 / SQLite (`better-sqlite3`) REST API for a book collection.

## Modules

| File | Responsibility |
|------|----------------|
| `src/index.ts` | Entry point — `app.listen(PORT)`. |
| `src/app.ts` | Express app: `express.json()`, `/health`, mounts `/books` router, 404 fallback. Exports `app` + `PORT` so tests import without starting a listener. |
| `src/db.ts` | Lazy singleton `better-sqlite3` connection (`books.db` in cwd), WAL mode, `CREATE TABLE IF NOT EXISTS books`. `getDb()` / `closeDb()`. |
| `src/validation.ts` | `Book`/`CreateBookInput`/`UpdateBookInput` interfaces + `validateCreateBook` / `validateUpdateBook` returning string[] of errors. |
| `src/routes/books.ts` | CRUD router: prepared statements for POST/GET(list+filter)/GET(:id)/PUT/DELETE, with 201/200/404/400/409/204 codes. |
| `tests/books.test.ts` | 14 supertest integration tests across all endpoints. |

## Request flow

`index.ts → app.ts → routes/books.ts → db.ts (prepared statement) → SQLite`. Validation runs in the route handler before any DB write. The schema enforces `UNIQUE(isbn)`; the router maps the unique-constraint error to HTTP 409.

## Notes

- Clean layering (app / routes / db / validation separated).
- Tests import `app` directly (no network), reset the DB file per test.
