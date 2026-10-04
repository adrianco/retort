# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, route handlers, SQLite access, validation | `main()`, `NewAPI()`, `(*API).Routes()`, `Book` |
| main_test.go | httptest-based integration tests | 4 test functions |
