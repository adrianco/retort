# Books API

A small ASP.NET Core REST API for managing a book collection. Book records are stored in SQLite.

## Requirements

- .NET 10 SDK

## Run

From this directory:

```sh
dotnet run --project BooksApi
```

The service listens at the URL printed by ASP.NET Core. It creates `books.db` in the working directory on first run. To use a different SQLite connection string, set `BookDb__ConnectionString`, for example `Data Source=/tmp/my-books.db`.

## API

- `GET /health` — health status
- `POST /books` — create a book; JSON body: `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`
- `GET /books` — list books; optionally filter with `?author=Frank%20Herbert`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book using the same JSON shape as create
- `DELETE /books/{id}` — delete a book

Title and author are required for create and update. Create returns `201 Created`, update/get return `200 OK`, delete returns `204 No Content`, missing books return `404 Not Found`, and invalid input returns `400 Bad Request`.

## Build and test

```sh
dotnet build BooksApi.sln
dotnet test BooksApi.sln
```
