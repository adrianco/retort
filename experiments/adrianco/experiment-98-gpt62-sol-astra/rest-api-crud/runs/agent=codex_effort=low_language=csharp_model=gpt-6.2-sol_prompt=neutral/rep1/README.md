# Book Collection API

An ASP.NET Core REST API backed by a SQLite database.

## Setup and run

Install the .NET 10 SDK, then run these commands from the workspace directory.

```sh
dotnet restore Books.Api.csproj
dotnet run --project Books.Api.csproj -- --urls http://localhost:5000
```

The service creates `books.db` in the application content root on startup. Set the
`Books__DatabasePath` environment variable to use a different file. Its parent
directory must already exist and be writable.

```sh
curl http://localhost:5000/health
curl -i http://localhost:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"}'
curl 'http://localhost:5000/books?author=Octavia%20Butler'
```

| Method and path | Result |
| --- | --- |
| `GET /health` | `200 OK` with `{"status":"ok"}` |
| `POST /books` | `201 Created` with the new book and a `Location` header |
| `GET /books` | `200 OK` with a JSON array, ordered by ID |
| `GET /books/{id}` | `200 OK` with the book, or `404 Not Found` |
| `PUT /books/{id}` | `200 OK` with the updated book, or `404 Not Found` |
| `DELETE /books/{id}` | `204 No Content`, or `404 Not Found` |

POST and PUT require nonblank `title` and `author` strings. Invalid input
returns `400 Bad Request`. The optional fields are `year` (integer) and `isbn`
(string). PUT replaces the book's fields and clears omitted optional values.
The `author` filter matches the full author name with SQLite's ASCII
case-insensitive comparison.

## Tests

```sh
dotnet test Tests/Books.Tests.csproj
```

For environments that block the test runner's loopback connection, run the same
integration tests in-process with `dotnet run --project Tests/Books.Tests.csproj`.

The integration tests cover health, creation and persistence, author filtering,
updates and deletion, missing IDs, required fields, and malformed JSON.
