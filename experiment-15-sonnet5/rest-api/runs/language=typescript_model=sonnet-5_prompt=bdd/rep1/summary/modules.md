# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | Express app factory; all HTTP route handlers | `createApp(db)` |
| src/db.ts | SQLite connection + `books` table schema | `createDatabase(filename)` |
| src/validation.ts | Required-field / type validation for book input | `validateBookInput(input, opts)`, `ValidationResult` |
| src/types.ts | Domain type definitions | `Book`, `BookInput` |
| src/server.ts | Process entry point; wires DB + app and listens | (top-level `app.listen`) |
| tests/books.test.ts | BDD (Given/When/Then) Supertest integration tests | 14 test cases |
