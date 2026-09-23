# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | HTTP server, routing, SQLite store, validation | `createApp()`, `createBookStore()`, `validateBook()`, `Book` |
| test/books.test.ts | Store + validation unit tests (node:test) | 4 test functions |
