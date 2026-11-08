# Architecture summary

A small Elixir/Plug REST service for a book collection, persisted in SQLite via Ecto.

## Modules

| File | Role |
|------|------|
| `lib/book_collection/application.ex` | OTP application: starts `Repo` under a supervisor, creates the `books` table if absent, and (outside `:test`) starts Bandit serving the router on the configured port. |
| `lib/book_collection/router.ex` | `Plug.Router` with all endpoints: `/health`, `/books` (list + `?author=` filter), `POST/GET/PUT/DELETE /books/:id`. Private helpers: `parse_json` (Plug.Parsers, 400 on malformed JSON), `with_book` (id parse + 404), `save` (changeset insert_or_update, 422 on errors), `json` (encode + content-type). |
| `lib/book_collection/book.ex` | Ecto schema `books` (title, author, year, isbn) + `changeset/2` with `validate_required([:title, :author])`; `json/1` projects the public fields. |
| `lib/book_collection/repo.ex` | `Ecto.Repo` with the `Ecto.Adapters.SQLite3` adapter. |
| `config/config.exs` | DB path (env `DATABASE_PATH`), port (env `PORT`), and `:start_server` disabled under `:test`. |

## Flow

Request → `Plug.Router` `:match` → `parse_json` → `:dispatch` → endpoint handler → `Repo` (Ecto/SQLite) → `Jason`-encoded JSON response. Validation failures flow through `save/3` → `traverse_errors` → 422. Unknown routes → `match _` → 404.

## Test strategy

`test/router_test.exs` drives the router in-process with `Plug.Test.conn/3` (no live server; `:start_server` false in test). 5 tests cover health, full CRUD lifecycle, list+author filter, malformed-JSON handling, and required-field/type validation. Each test resets the table in `setup`.
