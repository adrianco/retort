# Book collection API

An ASP.NET Core API backed by SQLite. Requires the .NET 10 SDK.

```sh
dotnet restore Books.csproj
dotnet run --project Books.csproj
```

The application prints its listening URL at startup. By default it creates `books.db` in the working directory. Set `ConnectionStrings__Books` to a SQLite connection string to use another database, for example `Data Source=/tmp/books.db`.

Endpoints:

- `GET /health` — service health.
- `POST /books` — create a book; returns 201 with a Location header.
- `GET /books` — list books; optional `author` query parameter matches the whole author name, case-insensitively for ASCII characters.
- `GET /books/{id}` — retrieve a book.
- `PUT /books/{id}` — replace the book fields.
- `DELETE /books/{id}` — delete a book; returns 204.

Create and update accept JSON such as `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`. Title and author must contain non-whitespace text; year and isbn are optional. Missing IDs return 404 and invalid input returns 400.

Run the integration tests with:

```sh
dotnet test tests/Books.Tests.csproj
```
