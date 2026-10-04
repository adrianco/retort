# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite persistence, route handlers | `main()`, `OpenDB()`, `NewServer()`, `Server.Handler()` |
| main_test.go | httptest-based API integration tests | 5 test functions (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListAndAuthorFilter`, `TestNotFoundAndBadID`) |
