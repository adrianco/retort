# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite init, all six route handlers | `Book`, `initDB()`, `healthHandler`, `createBookHandler`, `getBooksHandler`, `getBookHandler`, `updateBookHandler`, `deleteBookHandler`, `main()` |
| main_test.go | Handler-level tests using `httptest` + testify | 6 test functions (`TestHealthCheck`, `TestCreateBook`, `TestCreateBookMissingFields`, `TestGetBookByID`, `TestUpdateBook`, `TestDeleteBook`) |
| go.mod / go.sum | Module `book-api`, Go 1.21; deps `mattn/go-sqlite3`, `stretchr/testify` | — |
| README.md | Setup, build, run, curl usage examples | — |
