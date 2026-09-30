# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `main.go:health` |
| POST | /books | `Book (201) \| 400` | `main.go:create` |
| GET | /books | `[Book] (200)`, optional `?author=` filter | `main.go:list` |
| GET | /books/{id} | `Book (200) \| 400 \| 404` | `main.go:get` |
| PUT | /books/{id} | `Book (200) \| 400 \| 404` | `main.go:update` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `main.go:delete` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## Library API

`Store` methods: `NewStore(dsn)`, `Create`, `List(author)`, `Get(id)`, `Update`, `Delete`, `Ping`, `Close`.
