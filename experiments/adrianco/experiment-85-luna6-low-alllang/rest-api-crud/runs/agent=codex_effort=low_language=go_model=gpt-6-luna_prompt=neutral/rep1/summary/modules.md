# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, router, CRUD handlers, SQLite access, JSON helpers | `main()`, `NewAPI()`, `API.ServeHTTP`, `openDB()` |
| main_test.go | httptest-based integration tests over `API.ServeHTTP` | 3 test functions |
| go.mod / go.sum | Module `bookapi`, single direct dep `modernc.org/sqlite` | — |
| README.md | Setup, run, endpoint, and test instructions | — |
