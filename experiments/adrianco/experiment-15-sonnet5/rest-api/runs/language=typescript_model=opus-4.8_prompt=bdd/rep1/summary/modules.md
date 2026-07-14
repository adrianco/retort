# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/db.ts | SQLite connection + schema (via Node's built-in `node:sqlite`), Book types | `createDatabase()`, `Book`, `BookInput` |
| src/repository.ts | Data-access layer wrapping prepared statements | `BookRepository` (`create`/`findAll`/`findById`/`update`/`delete`) |
| src/validation.ts | Request-body validation & normalisation | `validateBook()`, `ValidationResult` |
| src/app.ts | Express app factory, route handlers | `createApp(db)` |
| src/server.ts | Process entry point — opens DB, starts listener | (top-level `app.listen`) |
| tests/books.test.ts | BDD integration tests (supertest + in-memory DB) | 12 test cases |
