# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/db.ts | SQLite schema + data access (node:sqlite) | `openDatabase()`, `BookRepository`, `Book`, `BookInput` |
| src/validation.ts | Request-body validation + id parsing | `validateBook()`, `parseId()`, `ValidationResult` |
| src/app.ts | HTTP server, routing, JSON/error handling | `createApp()` |
| src/server.ts | Process entry point, env config, shutdown | (module main) |
| test/api.test.ts | API integration tests (node:test) | 19 test cases |
