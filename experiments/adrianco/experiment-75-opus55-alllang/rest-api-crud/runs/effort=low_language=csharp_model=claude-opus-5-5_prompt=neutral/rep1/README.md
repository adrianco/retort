# Book API

ASP.NET Core (.NET 10) minimal API for managing books, stored in SQLite.

## Run
```
dotnet run --project src/BookApi
```
Data is stored in `books.db` by default; override with `--ConnectionString "Data Source=path.db"`.

## Endpoints
- `GET /health`
- `POST /books` — body `{ "title", "author", "year", "isbn" }` (title and author required) → 201
- `GET /books[?author=Name]` — case-insensitive author filter
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` → 200 / 400 / 404
- `DELETE /books/{id}` → 204 / 404

Validation errors return 400 with a problem-details JSON body.

## Test
```
dotnet test
```
