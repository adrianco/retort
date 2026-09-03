# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.go` | HTTP server, SQLite persistence, all route handlers | `Book`, `initDB()`, `healthCheck()`, `getBooks()`, `getBook()`, `createBook()`, `updateBook()`, `deleteBook()`, `main()` |
| `main_test.go` | `httptest`-based handler tests | `TestMain` + 9 test functions |
| `test_api.sh` | Manual smoke script: starts the built binary and curls each endpoint | shell script, no exported symbols |
| `README.md` | Setup, run, test and curl-example documentation | — |
| `go.mod` / `go.sum` | Module `book-api`, Go 1.26.6, single dependency `github.com/mattn/go-sqlite3 v1.14.50` | — |

Single-package layout: everything is `package main` in one file plus one test file. No `internal/`, no separate model/store/handler packages.
