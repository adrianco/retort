# Book Collection API

An ASP.NET Core REST API for managing books, backed by SQLite.

## Requirements

- .NET 10 SDK

## Run

From the workspace directory:

```sh
dotnet restore BookCollection.Api/BookCollection.Api.csproj
dotnet run --project BookCollection.Api
```

The API listens at the URL printed by `dotnet run`. SQLite creates `books.db` in the process working directory on first launch. Set the `ConnectionStrings__Books` environment variable to change the connection string.

## Endpoints

- `GET /health`
- `POST /books` with JSON `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "..." }`
- `GET /books` (optional `?author=...` filter)
- `GET /books/{id}`
- `PUT /books/{id}` with the same JSON fields as create
- `DELETE /books/{id}`

Title and author are required. Missing records return `404`; create returns `201`; successful deletion returns `204`; validation errors return `400` with a JSON problem response.

## Tests

```sh
dotnet test BookCollection.Tests/BookCollection.Tests.csproj
```
