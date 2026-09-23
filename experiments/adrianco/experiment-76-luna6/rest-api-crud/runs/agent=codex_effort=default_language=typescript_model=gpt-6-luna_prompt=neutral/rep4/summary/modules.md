# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | HTTP server + route handlers, SQLite table setup, input validation | `createApp()`, `createHandler(db)` |
| src/server.ts | Process entry point: binds port, wires SIGINT/SIGTERM shutdown | (top-level), `shutdown()` |
| tests/books.test.ts | node:test integration tests against `createHandler` with in-memory SQLite | 4 test functions |
