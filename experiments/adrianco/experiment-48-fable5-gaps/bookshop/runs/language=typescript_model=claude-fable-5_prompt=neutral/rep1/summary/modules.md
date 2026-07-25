# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Process entry: wires db + app, reads PORT/DB_PATH env, listens | (top-level script) |
| src/app.ts | Express app factory, all route handlers, JSON error middleware | `createApp(db)`, `parseId()` |
| src/db.ts | SQLite (node:sqlite) connection + schema creation | `createDb(path)`, `Book` interface |
| src/validation.ts | Book input validation for POST/PUT | `validateBookInput(body)`, `BookInput`, `ValidationResult` |
| test/books.test.ts | Supertest+vitest integration tests over `createApp` | 18 `it` tests across 6 `describe` blocks |
