# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | Express app factory, validation, route handlers, error middleware | `createApp()`, `ValidationError` |
| src/db.ts | SQLite connection + schema init (better-sqlite3) | `createDb()`, `Book` |
| src/server.ts | Process entry point; binds `createApp()` to a port | top-level `app.listen` |
| tests/books.test.ts | API integration tests over an in-memory DB | 21 test cases (`it(...)`) |
