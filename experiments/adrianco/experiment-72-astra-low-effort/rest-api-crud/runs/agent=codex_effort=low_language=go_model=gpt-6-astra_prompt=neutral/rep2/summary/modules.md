# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, router, SQLite-backed CRUD handlers, graceful shutdown | `main()`, `openDB()`, `newHandler()`, `API.ServeHTTP` |
| main_test.go | httptest-based integration tests | `TestBookLifecycle`, `TestAuthorFilter`, `TestValidation`, `TestRoutingAndHealth`, `TestPersistence` |
