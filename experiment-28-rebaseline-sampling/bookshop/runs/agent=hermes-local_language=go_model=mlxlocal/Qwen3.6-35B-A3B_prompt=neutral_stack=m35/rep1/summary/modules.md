# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | HTTP server, SQLite persistence, all route handlers | `main`, `initDB`, `createBookHandler`, `listBooksHandler`, `getBookHandler`, `updateBookHandler`, `deleteBookHandler`, `healthHandler`, `validateBook` |
| app_test.go | Integration tests against a gin router bound to a temp SQLite DB | `TestMain` + 9 `Test*` functions |
| go.mod / go.sum | Module deps (gin, mattn/go-sqlite3) | — |
| README.md | Setup, run, and curl usage docs | — |
