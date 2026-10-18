# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / 400 / 409 | `api.cpp:create_book` |
| GET | /books | `{books:[Book]}` (200), `?author=` exact filter | `api.cpp:list_books` |
| GET | /books/{id} | `Book` (200) / 404 | `api.cpp:get_book` |
| PUT | /books/{id} | `Book` (200) / 404 / 400 / 409 | `api.cpp:update_book` |
| DELETE | /books/{id} | 204 / 404 | `api.cpp:delete_book` |
| GET | /health | `{status, database}` (200) | `api.cpp:dispatch` |

Unknown routes/ids → 404; wrong method on a known path → 405; malformed JSON/invalid field → 400; duplicate isbn → 409; unexpected error → 500.

## Library API

`books::handle_request(BookRepository&, const Request&) -> Response` — pure, socket-free core, directly testable.
`books::parse_book_input`, `books::to_json`, `books::BookRepository` CRUD.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT UNIQUE, nullable).
