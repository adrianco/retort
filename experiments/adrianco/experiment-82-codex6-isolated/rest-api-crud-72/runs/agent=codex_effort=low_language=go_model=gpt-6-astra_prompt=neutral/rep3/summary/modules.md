# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, CRUD handlers, SQLite access, graceful shutdown | `main`, `run`, `openDB`, `API.ServeHTTP`, `API.save`, `API.list`, `API.get` |
| main_test.go | httptest-based integration tests over the full HTTP surface | 5 test functions (`TestBookLifecycle`, `TestListAndAuthorFilter`, `TestValidation`, `TestRoutesAndHealth`, `TestPersistence`) |
| go.mod / go.sum | Module definition + pinned dependency (`github.com/mattn/go-sqlite3`) | — |
| README.md | Setup, run, and API documentation | — |
