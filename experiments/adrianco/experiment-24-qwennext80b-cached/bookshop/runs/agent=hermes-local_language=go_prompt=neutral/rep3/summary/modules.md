# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | Gin HTTP server, SQLite init, all route handlers | `main()`, `initDB()`, `CreateBook`, `GetBooks`, `GetBook`, `UpdateBook`, `DeleteBook`, `HealthCheck` |
| app_test.go | httptest-based integration tests | 11 `Test*` functions |
| go.mod / go.sum | Module deps (gin, go-sqlite3, testify) | — |
| README.md | Setup, run, and API documentation | — |
