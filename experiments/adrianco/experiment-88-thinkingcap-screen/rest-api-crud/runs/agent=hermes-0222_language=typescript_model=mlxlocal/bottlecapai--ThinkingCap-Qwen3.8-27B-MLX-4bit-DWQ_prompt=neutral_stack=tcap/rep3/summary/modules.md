# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Process entry point; opens the SQLite DB and starts the HTTP listener | top-level bootstrap (reads `DATABASE_PATH`/`PORT`) |
| src/app.ts | Express app factory and all route handlers | `createApp(database)` |
| src/db.ts | SQLite persistence layer (schema + CRUD) via `node:sqlite` | `openDb`, `closeDb`, `listBooks`, `getBook`, `createBook`, `updateBook`, `deleteBook`, `Book`, `BookFields` |
| src/validation.ts | Request-body validation for create/update | `validateBookPayload`, `MIN_YEAR`, `MAX_YEAR`, `MAX_TITLE_LENGTH`, `MAX_AUTHOR_LENGTH` |
| tests/books.test.ts | API integration tests (supertest against `createApp`) | 28 test cases |
| tests/validation.test.ts | Unit tests for `validateBookPayload` | 13 test cases |
