# Book collection API

Install the .NET 10 SDK, then run these commands from the project directory.

```sh
dotnet restore Books.csproj
dotnet run --project Books.csproj -- --urls http://localhost:5000
```

The service creates a SQLite database named `books.db` in the working directory. Set `ConnectionStrings__Books` to a SQLite connection string to use another location.

| Method | Path | Result |
| --- | --- | --- |
| GET | /health | 200 with the service status |
| POST | /books | 201 with the created book and its Location header |
| GET | /books | 200 with an array ordered by ID |
| GET | /books?author=Octavia%20Butler | 200 with exact, case-sensitive author matches |
| GET | /books/{id} | 200 with the book |
| PUT | /books/{id} | 200 with the replacement book |
| DELETE | /books/{id} | 204 on success |

Send a JSON object for POST and PUT. Both require nonblank title and author strings. Year is an optional integer and ISBN is an optional string. Omitting an optional field on PUT clears it. Invalid input returns 400 and a missing book returns 404.

```sh
curl -i http://localhost:5000/books -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
```

Run the integration tests with `dotnet test tests/Tests.csproj`. Each test uses the HTTP request pipeline and a temporary SQLite database.
