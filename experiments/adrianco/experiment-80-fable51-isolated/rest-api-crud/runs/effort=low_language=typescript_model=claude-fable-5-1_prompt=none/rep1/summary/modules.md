# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | Express app factory, route handlers, request validation | `createApp(store)`, `validateBook(body)` |
| src/db.ts | SQLite persistence via `node:sqlite`, book CRUD | `BookStore`, `Book`, `BookInput` |
| src/server.ts | Process entry point — binds port, opens file-backed DB | (top-level `listen`) |
| tests/books.test.ts | HTTP integration tests against an in-memory store | 8 `node:test` cases |
