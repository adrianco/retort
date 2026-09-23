# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookStore.h | Persistence interface | `BookStore` |
| src/BookStore.m | SQLite CRUD over the `books` table | `initWithPath:`, `createBook:`, `listBooksByAuthor:`, `bookWithId:`, `updateBook:with:`, `deleteBook:` |
| src/BookAPI.h | Transport-independent router + response type | `BookAPI`, `APIResponse` |
| src/BookAPI.m | Request routing, JSON validation, status codes | `handleMethod:target:body:`, `validate:error:` |
| src/main.m | HTTP/1.1 server: BSD socket accept loop + request parsing | `main`, `handleClient`, `reason` |
| tests/tests.m | Integration tests driving the router with in-memory SQLite | `main` (21 assertions) |
