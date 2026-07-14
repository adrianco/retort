# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,timestamp}` | `handlers.go:HandleHealth` |
| POST | /books | `201 Book` \| `400 ErrorResponse` | `handlers.go:HandleCreateBook` |
| GET | /books | `200 [Book]` (optional `?author=` LIKE filter) | `handlers.go:HandleListBooks` |
| GET | /books/{id} | `200 Book` \| `404` | `handlers.go:HandleGetBook` |
| PUT | /books/{id} | `200 Book` \| `404` | `handlers.go:HandleUpdateBook` |
| DELETE | /books/{id} | `204` \| `404` | `handlers.go:HandleDeleteBook` |

Routing is manual: `/books` and `/books/` are both bound to `HandleBooks`, which
dispatches on method and parses the trailing `{id}` with `strconv.Atoi`.

## Data schema

`books` table (SQLite, `modernc.org/sqlite` pure-Go driver):
id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null),
year (INTEGER not null), isbn (TEXT not null), created_at (DATETIME), updated_at (DATETIME).

## Request/response DTOs

- `CreateBookRequest` {title, author, year, isbn}
- `UpdateBookRequest` {*title, *author, *year, *isbn} — pointer fields enable partial update
- `ErrorResponse` {error, validation[]}
- `HealthResponse` {status, timestamp}
