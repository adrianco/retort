# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Entry point: binds port/DB from env, starts server, handles SIGINT/SIGTERM shutdown | top-level bootstrap |
| src/app.ts | HTTP routing, request parsing, error handling | `createApp(store)` |
| src/store.ts | SQLite-backed persistence via `node:sqlite` | `BookStore`, `Book` |
| src/validation.ts | Request-body validation for create/replace | `validateBook()`, `BookInput`, `ValidationResult` |
| tests/api.test.ts | Integration tests against an in-memory DB | 15 tests in 8 `describe` blocks |
