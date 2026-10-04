# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Process entry: builds store + app, binds `PORT` | top-level `listen()` |
| src/app.ts | Express app factory, all route handlers, JSON error handler | `createApp(store)` |
| src/db.ts | SQLite persistence via `node:sqlite` | `BookStore`, `Book`, `BookInput` |
| src/validation.ts | Request-body validation and id parsing | `validateBook()`, `parseId()` |
| tests/books.test.ts | API + persistence tests | 12 `it(...)` cases in 2 `describe` blocks |
