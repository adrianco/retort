# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `main.go` inline |
| POST | /books | `201 Book` / `400` | `main.go:server.create` |
| GET | /books | `200 [Book]` (optional `?author=`) | `main.go:server.list` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `main.go:server.get` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `main.go:server.update` |
| DELETE | /books/{id} | `204` / `400` / `404` | `main.go:server.delete` |

## Library API

`store.go`: `NewStore(dsn) (*Store, error)`, `(*Store).Create(*Book)`, `.Get(id)`, `.List(author)`, `.Update(*Book)`, `.Delete(id)`, `.Close()`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').
