# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | HTTP server + all route handlers, SQLite table setup, body validation | `createApp()`, `validate()`, `Book` interface |
| src/server.ts | Process entry point — binds `createApp()` to a port from env | module main |
| tests/api.test.ts | node:test integration tests against a live in-memory server | 4 test functions |
