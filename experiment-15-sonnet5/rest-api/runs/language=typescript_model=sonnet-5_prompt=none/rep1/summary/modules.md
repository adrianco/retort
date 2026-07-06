# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Process entry — creates DB + app, starts HTTP listener | top-level; reads `PORT`, `DB_FILE` env |
| src/app.ts | Express app factory, all route handlers | `createApp(db)` |
| src/db.ts | SQLite (`node:sqlite`) connection + schema migration | `createDatabase(filename)` |
| src/validation.ts | Book input validation (full + partial) | `validateBookInput()`, `ValidationResult` |
| src/types.ts | Domain + input type definitions | `Book`, `BookInput` |
| tests/books.test.ts | Jest + Supertest integration tests | 8 test functions |
