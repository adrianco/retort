# Architecture summary — book-api (Elixir)

The `run-summary` skill is not available in this session; this is a hand-written summary.

## Modules

- `lib/book_api/application.ex` — OTP application; starts `Repo` and the Cowboy HTTP server.
- `lib/book_api/repo.ex` — Ecto repo using `Ecto.Adapters.SQLite3`.
- `lib/book_api/book.ex` — Ecto schema + `changeset/2` (validation: title/author required, year 1–9999, isbn ≤ 20).
- `lib/book_api/books.ex` — context: `list_books/1` (with `?author=` filter), `get_book/1`, `create_book/1`, `update_book/2`, `delete_book/1`.
- `lib/book_api/web/router.ex` — Plug.Router: `/health`, CRUD on `/books`, JSON serialization, 404/422 error shaping.
- `priv/repo/migrations/…_create_books.exs` — books table + author index.

## Flow

HTTP request → `Plug.Parsers` (JSON) → `Router` dispatch → `Books` context → `Repo` (SQLite) → JSON response with status code. Validation failures surface as 422 with per-field detail; unknown/malformed ids and routes return 404.

## Tests

- `test/book_api/router_test.exs` — 8 HTTP integration tests (health, full CRUD lifecycle, validation 422, missing-body 422, author filter, 404 cases, PUT invalid, unknown route).
- `test/book_api/books_test.exs` — 5 context unit tests.
