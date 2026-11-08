# Book collection API

Requires the .NET 10 SDK. From this directory:

```sh
dotnet restore Books.csproj
dotnet run --project Books.csproj
```

The console displays the listening URL. SQLite creates `books.db` in the working directory on first run. Set the `ConnectionStrings__Books` environment variable to a SQLite connection string to use another database, for example `Data Source=/tmp/books.db`.

Run the integration tests with:

```sh
dotnet test tests/Books.Tests.csproj
```

Requests and responses use JSON. Create a book with `POST /books`, for example:

```json
{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
```

`title` and `author` are required and cannot be blank. `year` (integer) and `isbn` (string) are optional. `PUT /books/{id}` replaces all fields using the same input format. `GET /books` lists books; `?author=Frank%20Herbert` filters by exact author, case-insensitively for ASCII characters. `GET /books/{id}` fetches one, and `DELETE /books/{id}` removes one. `GET /health` returns service status. Creation returns 201 and a Location header, deletion returns 204, missing IDs return 404, and invalid input returns 400.

If the test runner cannot open local sockets in a restricted environment, run the same tests in-process with `dotnet run --project tests/Books.Tests.csproj`.
