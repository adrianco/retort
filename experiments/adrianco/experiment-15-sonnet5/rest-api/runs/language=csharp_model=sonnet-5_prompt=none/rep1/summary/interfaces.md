# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `Program.cs:26` |
| POST | /books | `201 Book` / `400` | `Program.cs:28` |
| GET | /books | `200 [Book]` (opt. `?author=` partial, case-sensitive) | `Program.cs:50` |
| GET | /books/{id} | `200 Book` / `404` | `Program.cs:63` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `Program.cs:69` |
| DELETE | /books/{id} | `204` / `404` | `Program.cs:93` |

## Data schema

`Books` table (EF Core, SQLite): Id (int, pk, identity), Title (string), Author (string), Year (int?, nullable), Isbn (string?, nullable). Schema created at startup via `db.Database.EnsureCreated()`.

## Library API

`BookRequest` DTO: Title (required, non-empty), Author (required, non-empty), Year?, Isbn?. Validated via `Validator.TryValidateObject` on POST and PUT.
