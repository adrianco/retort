# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` \| `503` | `books.go:health` |
| POST | /books | `201 Book` \| `400` | `books.go:books` |
| GET | /books | `200 [Book]` (optional `?author=`) | `books.go:books` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `books.go:book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `books.go:book` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `books.go:book` |

Routing uses `net/http` `ServeMux` with `/books` (collection) and `/books/` (item) patterns; the item handler parses the trailing id.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## CLI / Library API

(none — single `package main` binary)
