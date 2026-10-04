# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `lib.rs` inline closure |
| POST | /books | 201 `Book` + `Location` header; 400 on invalid | `lib.rs:create` |
| GET | /books | 200 `[Book]` (optional `?author=` exact filter) | `lib.rs:list` |
| GET | /books/{id} | 200 `Book`; 404 if absent; 400 non-integer id | `lib.rs:fetch` |
| PUT | /books/{id} | 200 `Book`; 404 if absent; 400 on invalid | `lib.rs:update` |
| DELETE | /books/{id} | 200 `{"deleted":id}`; 404 if absent | `lib.rs:delete` |
| (any) | fallback | 404 `{"error":...}` / 405 method-not-allowed | inline fallbacks |

## Library API

`app(connection: Connection) -> Result<Router, rusqlite::Error>` — builds the router, creates the `books` table, wires shared `Arc<Mutex<Connection>>` state.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, CHECK trimmed length > 0), `author` (TEXT NOT NULL, CHECK trimmed length > 0), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
