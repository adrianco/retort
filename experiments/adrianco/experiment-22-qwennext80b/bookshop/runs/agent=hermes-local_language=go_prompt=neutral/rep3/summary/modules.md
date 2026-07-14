# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Wires DB, migrates schema, registers routes, starts HTTP server on :8080 | `main()` |
| server.go | Models, DB init, and all HTTP handlers | `Book`, `Handler`, `NewHandler()`, `InitDB()`, `handleHealth`, `handleBooks`, `handleBookByID` |
| server_test.go | httptest-based handler tests + GORM model test | 10 `Test*` functions (incl. `TestMain`) |
