# Book Collection API (C# / ASP.NET Core Minimal API + SQLite)

## Requirements
- .NET 10 SDK

## Run
```bash
dotnet run --project src/BookApi
```
Data is stored in `books.db` (override with `--Database "Data Source=path.db"`).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201; 400 if title/author missing |
| GET | /books | optional `?author=` (case-insensitive exact match) |
| GET | /books/{id} | 200 / 404 |
| PUT | /books/{id} | full update, 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

## Test
```bash
dotnet test
```
Tests use an isolated in-memory SQLite database per test.
