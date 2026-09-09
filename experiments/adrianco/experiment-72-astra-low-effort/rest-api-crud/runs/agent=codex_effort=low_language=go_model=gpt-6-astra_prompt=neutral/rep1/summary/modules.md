# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, SQLite persistence, all handlers | `main()`, `run()`, `API`, `API.ServeHTTP`, `openDB()` |
| main_test.go | HTTP integration tests against an isolated temp SQLite DB | 5 test functions (`TestCRUD`, `TestListAndFilter`, `TestValidation`, `TestRoutingAndHealth`, `TestPersistence`) |
| go.mod | Module + Go 1.22 toolchain | `module rest-api-crud` |
| go.sum | Dependency checksums | `github.com/mattn/go-sqlite3` |
| README.md | Setup, run, and API documentation | — |
