# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite store, route handlers | `Book`, `Server`, `NewServer()`, `Handler()`, `main()` |
| main_test.go | httptest integration tests | 4 test functions (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListFilter`) |
| go.mod / go.sum | Module + pinned deps (`modernc.org/sqlite`) | — |
| README.md | Setup, run, endpoint reference | — |
