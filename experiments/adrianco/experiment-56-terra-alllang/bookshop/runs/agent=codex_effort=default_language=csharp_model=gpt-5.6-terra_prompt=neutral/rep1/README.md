# Book Collection API

An ASP.NET Core REST API backed by SQLite for creating, listing, updating, and deleting books.

## Run

Requires the .NET 10 SDK.

```bash
dotnet run --project BookCollection.Api
```

The API listens on the URL shown by `dotnet run`. Its SQLite database is created automatically as `books.db` in the working directory. Set `Database__Path` to use a different database file.

## Endpoints

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/health` | Health status (`200 OK`) |
| `POST` | `/books` | Creates a book (`201 Created`) |
| `GET` | `/books` | Lists books; use `?author=name` to filter by author |
| `GET` | `/books/{id}` | Gets one book (`404` if missing) |
| `PUT` | `/books/{id}` | Updates one book (`404` if missing) |
| `DELETE` | `/books/{id}` | Deletes one book (`204 No Content`, or `404` if missing) |

`POST` and `PUT` accept JSON such as:

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required. Invalid input returns `400 Bad Request` with JSON validation details.

## Test

```bash
dotnet test BookCollection.slnx
```
