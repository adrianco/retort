# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `lib.rs:health` |
| POST | /books | `201 Book` + `Location` header; `422` validation; `400` bad JSON | `lib.rs:create_book` |
| GET | /books | `200 [Book]`, optional `?author=` filter (case-insensitive exact) | `lib.rs:list_books` |
| GET | /books/{id} | `200 Book` \| `404` | `lib.rs:get_book` |
| PUT | /books/{id} | `200 Book` \| `404` \| `422` validation | `lib.rs:update_book` |
| DELETE | /books/{id} | `204` \| `404` | `lib.rs:delete_book` |

## Data schema

`books` table (SQLite, `book.rs:init_schema`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

`book_api::app(Connection) -> Router` builds the router and initialises the schema. `book` module exposes the repository functions (`insert`/`get`/`list`/`update`/`delete`) and `BookInput::validate`.
