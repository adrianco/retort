# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `Program.cs:19` minimal endpoint |
| GET | /books | `200 [BookDto]` (optional `?author=` exact-match filter) | `BooksController.GetAll` |
| GET | /books/{id:int} | `200 BookDto \| 404` | `BooksController.GetById` |
| POST | /books | `201 BookDto` + Location \| `400` | `BooksController.Create` |
| PUT | /books/{id:int} | `200 BookDto \| 404 \| 400` | `BooksController.Update` |
| DELETE | /books/{id:int} | `204 \| 404` | `BooksController.Delete` |

## Data schema

`Books` table (EF Core, SQLite): Id (int, pk, identity), Title (string, required),
Author (string, required), Year (int?, nullable), Isbn (string?, nullable).

## Validation

`[Required]` on `Title` and `Author` in `CreateBookRequest`/`UpdateBookRequest`;
`[ApiController]` triggers automatic `400 ProblemDetails` when validation fails.
