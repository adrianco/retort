# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | Process entry point: builds the repo + app and listens; graceful shutdown on SIGINT/SIGTERM | top-level bootstrap |
| src/app.ts | Express app factory; all HTTP route handlers + JSON error middleware | `createApp(repo)` |
| src/db.ts | SQLite persistence via `node:sqlite`; schema + CRUD | `BookRepository` |
| src/validation.ts | Payload + path-id validation | `validateBookInput()`, `parseId()` |
| src/types.ts | Shared type definitions | `Book`, `BookInput`, `ValidationError` |
| tests/books.test.ts | API integration tests (supertest) | 20 test cases |
| tests/validation.test.ts | Unit tests for validation/parseId | 6 test cases |
