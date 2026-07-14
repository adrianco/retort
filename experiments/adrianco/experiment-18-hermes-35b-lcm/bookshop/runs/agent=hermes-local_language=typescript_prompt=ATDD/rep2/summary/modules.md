# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | Express server + all HTTP route handlers | `createApp(db)`, `startServer(app)`, `shutdownDb` |
| src/db.ts | better-sqlite3 data-access layer (schema + CRUD + counts) | `createDb()`, `createBook()`, `getAllBooks()`, `getBook()`, `updateBook()`, `deleteBook()`, `clearAll()`, `COUNT_ALL()`, `COUNT_BY_AUTHOR()` |
| src/validation.ts | Input validation (title/author required) | `validateBook()`, `BookInput`, `ValidationError` |
| tests/acceptance.test.ts | ATDD acceptance tests through the HTTP API (supertest) | 17 `it` blocks |
| tests/unit.test.ts | Unit tests for validation + DB layer | 17 `it` blocks |
