# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite store, all route handlers | `main()`, `API`, `openDB()`, `API.ServeHTTP` |
| main_test.go | Integration tests (httptest + temp SQLite) | 5 `Test*` functions |
| README.md | Setup, run, and API documentation | — |
| go.mod / go.sum | Module + pinned deps (`modernc.org/sqlite`, pure Go) | — |
