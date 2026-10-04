# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books.ts | SQLite-backed data layer for books (schema + CRUD) | `Book`, `BookInput`, `BookStore` |
| src/server.ts | HTTP server and route handlers | `createApp()` |
| test/api.test.ts | API integration tests over a live server on an in-memory DB | 3 test functions |
