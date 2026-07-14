# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | Gin HTTP server, SQLite init, all CRUD + health route handlers | `main()`, `initDB()`, `healthHandler`, `createBookHandler`, `listBooksHandler`, `getBookHandler`, `updateBookHandler`, `deleteBookHandler`, `Book`, `CreateBookRequest`, `UpdateBookRequest` |
| app_test.go | httptest-based integration tests over the Gin router with a separate SQLite test DB | 13 `Test*` functions, `setupTestDB()`, `teardownTestDB()`, `setupTestRouter()`, `insertBook()` |

Notes:
- `go.mod` / `go.sum` are dependency manifests (module `book-api`; deps: `github.com/gin-gonic/gin`, `github.com/mattn/go-sqlite3`).
- `book-api` is a compiled binary artifact, `books.db`/`test_books.db` are runtime SQLite files — not source.
