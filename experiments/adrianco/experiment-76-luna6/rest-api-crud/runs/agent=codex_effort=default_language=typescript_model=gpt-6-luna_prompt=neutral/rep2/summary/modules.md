# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books.ts | HTTP server, route handlers, validation, SQLite persistence | `Book`, `createBookServer()` |
| src/server.ts | Process entry point — binds port, wires signal shutdown | (top-level, uses `createBookServer`) |
| src/books.test.ts | node:test integration tests against an in-memory DB | 4 test functions |
