# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite wiring, all route handlers | `main()`, `createTable()`, `healthHandler`, `booksHandler`, `bookHandler`, `listBooks`, `createBook`, `getBook`, `updateBook`, `deleteBook` |
| main_test.go | httptest-based unit/integration tests | 15 `Test*` functions + `TestMain` |
| go.mod / go.sum | Module definition and dependency checksums | `mattn/go-sqlite3`, `stretchr/testify` |
| README.md | Setup, run, and API usage docs | — |
