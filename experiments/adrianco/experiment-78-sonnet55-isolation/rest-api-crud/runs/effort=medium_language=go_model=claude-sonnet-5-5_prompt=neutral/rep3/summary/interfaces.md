# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `main.go` inline |
| POST | /books | `Book` (201) / error (400) | `main.go:server.create` |
| GET | /books | `[Book]` (200), `?author=` filter | `main.go:server.list` |
| GET | /books/{id} | `Book` (200) / 404 | `main.go:server.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `main.go:server.update` |
| DELETE | /books/{id} | 204 / 404 | `main.go:server.delete` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## Exported API

`Store` methods: `Create`, `List(author)`, `Get(id)`, `Update`, `Delete`, `Close`; constructor `NewStore(dsn)`.
