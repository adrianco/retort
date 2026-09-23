# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BookStore.h | SQLite persistence interface | `BookStore` |
| BookStore.m | SQLite-backed book CRUD with prepared statements + `NSLock` | `createBook:`, `booksByAuthor:`, `bookWithId:`, `updateBook:fields:`, `deleteBook:` |
| BookAPI.h | Transport-independent request router interface | `BookAPI`, `APIResponse` |
| BookAPI.m | Routing, input validation, JSON responses | `handleMethod:target:body:`, `validate:error:` |
| main.m | BSD-socket HTTP/1.1 server, per-connection dispatch | `main`, `handleClient`, `sendResponse` |
| tests.m | Direct `BookAPI` unit/integration tests (in-memory DB) | `main` (22 CHECK assertions) |
| Makefile | Build/test targets | `all`, `test`, `clean` |
| README.md | Setup, run and endpoint docs | — |
