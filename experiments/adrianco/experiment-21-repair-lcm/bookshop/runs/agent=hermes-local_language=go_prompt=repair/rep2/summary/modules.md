# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server setup, route registration on `net/http` ServeMux | `main()` |
| models.go | Data structs and shared errors | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `ErrorResponse`, `ErrNotFound` |
| database.go | SQLite persistence via `modernc.org/sqlite`, repository interface + impl | `BookRepository`, `SQLiteRepo`, `NewSQLiteRepo()`, `Close()`, `CreateBook()`, `ListBooks()`, `GetBook()`, `UpdateBook()`, `DeleteBook()` |
| handlers.go | HTTP handler methods, validation, JSON encoding | `Handler`, `NewHandler()`, `healthCheck`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `writeJSON()` |
| integration_test.go | Integration/unit tests over handlers and repo | 16 test functions (`TestCreateBook`, `TestListBooks`, `TestListBooksFilterByAuthor`, `TestGetBook`, `TestUpdateBook`, `TestDeleteBook`, `TestSQLitePersistence`, `TestHTTPStatusCodes`, `TestValidationRequiredFields`, `TestHealthCheck`, `TestBookModel`, `TestErrNotFound`, `TestUpdateBookNotFound`, `TestDeleteBookNotFound`, plus helpers `createBook`, `setupRoutes`) |
