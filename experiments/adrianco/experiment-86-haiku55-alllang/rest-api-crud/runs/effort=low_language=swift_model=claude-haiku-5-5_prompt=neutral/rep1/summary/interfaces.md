# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `Routes.swift:buildRouter` |
| POST | /books | `Book` (201) / error (400) | `Routes.swift:buildRouter` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `Routes.swift:buildRouter` |
| GET | /books/{id} | `Book` (200) / 404 / 400 (non-int id) | `Routes.swift:buildRouter` |
| PUT | /books/{id} | `Book` (200) / 404 / 400 | `Routes.swift:buildRouter` |
| DELETE | /books/{id} | 204 / 404 / 400 | `Routes.swift:buildRouter` |

## Library API

- `BookStore` actor: `init(path:)`, `create(_:)`, `list(author:)`, `find(id:)`, `update(id:with:)`, `delete(id:)`
- `BookValidator.validate(_:maxYear:)` → `BookDraft`, throws `ValidationError`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT, nullable).
