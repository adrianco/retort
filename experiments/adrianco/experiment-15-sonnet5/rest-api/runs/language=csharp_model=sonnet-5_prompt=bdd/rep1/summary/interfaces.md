# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 BookResponse` (+ Location) / `400` | `BooksController.CreateBook` |
| GET | /books | `200 [BookResponse]` | `BooksController.ListBooks` |
| GET | /books?author= | `200 [BookResponse]` (filtered) | `BooksController.ListBooks` |
| GET | /books/{id} | `200 BookResponse` / `404` | `BooksController.GetBook` |
| PUT | /books/{id} | `200 BookResponse` / `404` / `400` | `BooksController.UpdateBook` |
| DELETE | /books/{id} | `204` / `404` | `BooksController.DeleteBook` |
| GET | /health | `200 {status:"healthy"}` | `HealthController.Get` |

## Data schema

`Books` table (EF Core `EnsureCreated`): Id (int, pk, identity), Title (string, non-null),
Author (string, non-null), Year (int, nullable), Isbn (string, nullable).

## Validation

`BookRequest` uses DataAnnotations `[Required(AllowEmptyStrings = false)]` on `Title` and
`Author`; `[ApiController]` auto-returns `400` with a `ValidationProblemDetails` body.
