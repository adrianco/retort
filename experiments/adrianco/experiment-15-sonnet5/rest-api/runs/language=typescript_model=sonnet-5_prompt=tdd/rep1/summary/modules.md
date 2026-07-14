# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/db.ts | SQLite connection + schema setup (`books` table) | `createDb(path)` |
| src/app.ts | Express app and all route handlers | `createApp(db)`, local `getBookById` helper |
| src/server.ts | Process entry point; wires db + app, listens on PORT | (top-level, `app.listen`) |
| tests/health.test.ts | Health endpoint integration test | 1 test |
| tests/books.test.ts | CRUD/validation/filter integration tests | 12 tests |
