# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite persistence, all route handlers | `main()`, `newAPI()`, `initDB()`, `Book` |
| main_test.go | httptest-based integration tests (in-memory SQLite) | 5 test functions |
