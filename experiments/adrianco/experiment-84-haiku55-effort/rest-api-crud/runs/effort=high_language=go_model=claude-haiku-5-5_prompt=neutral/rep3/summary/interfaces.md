# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` / `503` | `server.go:health` (pings DB) |
| POST | /books | `201 Book` + `Location` / `400` | `server.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `server.go:listBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `server.go:getBook` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `server.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `server.go:deleteBook` |

All responses are `application/json` except `204 No Content` on DELETE. Errors are `{"error": ...}`; validation errors are `{"error":"validation failed","fields":{...}}`.

## Library API

Exported package `bookapi`: `Book`, `BookInput`, `ValidationError`, `Store`, `OpenStore`, `NewHandler`, `ErrNotFound`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').
