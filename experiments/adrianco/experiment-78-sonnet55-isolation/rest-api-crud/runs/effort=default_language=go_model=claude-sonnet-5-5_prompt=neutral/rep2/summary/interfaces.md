# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:ok}` (200) | inline in `newHandler` |
| POST | /books | `Book` (201) / 400 | `main.go:server.create` |
| GET | /books | `[Book]` (200), `?author=` filter | `main.go:server.list` |
| GET | /books/{id} | `Book` (200) / 400 / 404 | `main.go:server.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `main.go:server.update` |
| DELETE | /books/{id} | 204 / 400 / 404 | `main.go:server.delete` |

## Library API

`store.go`: `NewStore(dsn) (*Store, error)`, `(*Store).Create/List/Get/Update/Delete/Close`.

## Data schema

`books` table: `id` (int pk autoincrement), `title` (text not null), `author` (text not null), `year` (int default 0), `isbn` (text default '').
