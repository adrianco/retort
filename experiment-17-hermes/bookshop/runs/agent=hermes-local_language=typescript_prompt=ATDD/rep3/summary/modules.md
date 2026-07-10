# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Self-contained Express app: all CRUD routes + `/health`, SQLite via `sqlite`/`sqlite3`. No exports; starts a listener. | `initDatabase()`, `startServer()` (no module export) |
| src/server.ts | Alternate Express bootstrap; `export default app`, delegates to `./routes/books` and `./database`. **Both imports point to files that do not exist.** | `app` (default export) |
| src/__tests__/book.api.test.ts | supertest acceptance tests for `/health` and `POST /books`. Imports `./src/index` (wrong path → unresolved). | 2 `it` blocks |
| src/__tests__/basic.test.ts | Placeholder unit test (`expect(1).toBe(1)`). | 1 `it` block |

Notes:
- Two competing, unreconciled app entrypoints (`index.ts` and `server.ts`) — neither is imported by a working test.
- No `src/database.ts`, no `src/routes/` directory exist despite `server.ts` importing them.
