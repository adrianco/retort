# Books API

A .NET 10 ASP.NET Core API with SQLite storage.

## Run

Install the .NET 10 SDK, then run:

```sh
dotnet restore BooksApi.csproj
dotnet run --project BooksApi.csproj --urls http://localhost:5000
```

The service creates `books.db` in its working directory. Set the `ConnectionStrings__Books` environment variable to a SQLite connection string to use a different database, for example `Data Source=/path/to/books.db`.

## API

- `POST /books` creates a book and returns `201` with a `Location` header.
- `GET /books` lists books; `?author=Herbert` filters by exact author (case-insensitive for ASCII characters).
- `GET /books/{id}` retrieves a book.
- `PUT /books/{id}` replaces a book's fields.
- `DELETE /books/{id}` deletes a book and returns `204`.
- `GET /health` returns a JSON health status.

Create and update accept JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`. Title and author must contain non-whitespace text; year and ISBN may be omitted or null. Invalid input returns `400`; missing books return `404`.

## Tests

```sh
dotnet test Tests/BooksApi.Tests.csproj
```
