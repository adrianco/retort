# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite setup, all route handlers | `main()`, `initDB()`, `booksHandler`, `singleBookHandler`, `healthHandler` |
| main_test.go | httptest-based handler tests | `TestMain`, `TestHealthCheck`, `TestCreateBook`, `TestCreateBookMissingRequiredFields`, `TestGetBooks` |
| go.mod / go.sum | Module + `mattn/go-sqlite3` dependency | — |
| README.md | Setup, run, and curl usage docs | — |
| demo.sh | Shell demo script exercising the endpoints | — |

Single-package (`package main`) Go project using the standard `net/http` mux; no framework.
