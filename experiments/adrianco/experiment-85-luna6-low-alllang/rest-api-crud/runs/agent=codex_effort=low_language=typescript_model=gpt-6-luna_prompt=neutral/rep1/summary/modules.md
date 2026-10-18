# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | Express app factory, route handlers, input validation, SQLite table bootstrap | `createApp()`, `Book`, `validateBook()` |
| src/server.ts | Process entry point: creates the app and listens on `PORT` | module main |
| tests/app.test.ts | Vitest integration tests driving handlers against an in-memory SQLite DB | 4 `it()` tests |
