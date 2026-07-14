# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handlers.rs:health` |
| POST | /books | `201 Book` \| `400` | `handlers.rs:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.rs:list_books` |
| GET | /books/:id | `200 Book` \| `404` | `handlers.rs:get_book` |
| PUT | /books/:id | `200 Book` \| `400` \| `404` | `handlers.rs:update_book` |
| DELETE | /books/:id | `204` \| `404` | `handlers.rs:delete_book` |

## Library API

`build_router(db: SharedDb) -> Router` — constructs the Axum router with all routes and shared state (`SharedDb = Arc<Mutex<Connection>>`).

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Error model

`AppError` enum → `NotFound` (404), `Validation(msg)` (400), `Internal(msg)` (500); all rendered as `{"error": ...}` JSON.
