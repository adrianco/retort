# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `handlers.go:HealthCheck` |
| POST | /books | `201 Book` / `400` | `handlers.go:CreateBook` |
| GET | /books | `200 [Book]` (opt. `?author=` filter) | `handlers.go:ListBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:GetBook` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:UpdateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `handlers.go:DeleteBook` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER not null), isbn (TEXT not null), created_at (DATETIME), updated_at (DATETIME). WAL journaling enabled.

## Library API

Go `package main` (not a reusable library). `Database` exposes CRUD methods; `Handler` binds them to HTTP. PUT uses partial-update semantics via pointer fields in `UpdateBookRequest`.
