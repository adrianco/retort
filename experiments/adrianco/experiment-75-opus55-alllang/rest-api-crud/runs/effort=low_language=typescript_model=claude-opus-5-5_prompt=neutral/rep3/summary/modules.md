# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Process entry: reads PORT/DB_PATH env, wires repo + app, listens | (top-level script) |
| src/app.ts | Express app factory, all route handlers, error middleware | `createApp(repo)` |
| src/db.ts | `node:sqlite` persistence layer, schema, CRUD | `BookRepository`, `Book`, `BookInput` |
| src/validate.ts | Request-body validation for create/update | `validateBook()`, `ValidationResult` |
| tests/books.test.ts | Vitest + supertest integration/unit tests | 9 test cases |
