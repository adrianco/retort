# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `app.go:healthCheck` |
| POST | /books | `201 {book} \| 400` | `app.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.go:listBooks` |
| GET | /books/:id | `200 {book} \| 404 \| 400` | `app.go:getBook` |
| PUT | /books/:id | `200 {book} \| 404 \| 400` | `app.go:updateBook` |
| DELETE | /books/:id | `200 {message} \| 404 \| 400` | `app.go:deleteBook` |

## Data schema

`books` table: id (int, pk, autoincrement), title (text, not null), author (text, not null), year (int, not null), isbn (text, **not null unique**).
