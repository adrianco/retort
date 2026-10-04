# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Process entry: builds store + app, listens, graceful shutdown | top-level bootstrap |
| src/app.ts | Express app factory, route handlers, id parsing, error handler | `createApp(store)` |
| src/db.ts | SQLite-backed book store (node:sqlite) | `BookStore`, `Book` |
| src/validation.ts | Request-body validation + normalization | `validateBook()`, `BookInput`, `ValidationResult` |
| tests/books.test.ts | HTTP integration tests against an in-memory DB | 12 `it` tests |
