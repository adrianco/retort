# Book Collection API

ASP.NET Core (.NET 10) minimal API backed by SQLite (`Microsoft.Data.Sqlite`).

## Run
```bash
dotnet run --project src/BookApi
```
Data is stored in `books.db` (override with `--ConnectionString "Data Source=other.db"`).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201 / 400 |
| GET | /books?author= | list, optional case-insensitive author filter |
| GET | /books/{id} | 200 / 404 |
| PUT | /books/{id} | full update → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

`title` and `author` are required; validation errors return `{"errors":[...]}`.

## Test
```bash
dotnet test
```
