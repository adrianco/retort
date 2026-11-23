# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite store, all route handlers | `main()`, `api.ServeHTTP`, `openDB()`, `api.list`, `api.save` |
| main_test.go | API integration tests (httptest, in-memory + temp-file DB) | `TestLifecycle`, `TestFilteringAndPersistence`, `TestValidationAndHealth` |
