# Architecture Summary — Book API (Elixir / Plug + Bandit + SQLite)

*Produced inline by evaluate-run (run-summary not sub-invoked; small 4-module codebase).*

## Modules

| Module | File | Responsibility |
|--------|------|----------------|
| `BookApi.Application` | `lib/book_api/application.ex` | OTP application; supervises the `Store` GenServer and (unless `server: false`) the Bandit HTTP listener. |
| `BookApi.Router` | `lib/book_api/router.ex` | `Plug.Router` HTTP layer: routes, JSON encoding, status codes, error handling. |
| `BookApi.Store` | `lib/book_api/store.ex` | GenServer owning a single SQLite connection (Exqlite); serializes all CRUD statements. |
| `BookApi.Book` | `lib/book_api/book.ex` | Pure validation of request bodies → `{:ok, attrs}` / `{:error, errors}`. |

## Interfaces

- **HTTP** (`Router`): `GET /health`, `POST /books`, `GET /books` (+`?author=`), `GET /books/:id`, `PUT /books/:id`, `DELETE /books/:id`, catch-all JSON 404.
- **Store API**: `create/1`, `list/0..1`, `get/1`, `update/2`, `delete/1`, `delete_all/0` (test helper).
- **Validation**: `Book.validate/1` — `title`/`author` required non-blank strings; `year` optional integer; `isbn` optional string.

## Flow

Request → `Plug.Parsers` (JSON) → route → `Book.validate` (for writes) → `Store` GenServer call → SQLite → `Jason.encode!` → response. `Plug.ErrorHandler` maps parser failures to 400/415.

## Config

`config/config.exs` sets prod DB `books.db`, port 4000; test env uses `:memory:` DB and `server: false` so tests drive `Router.call/2` directly. `config/runtime.exs` reads `PORT`/`DATABASE_PATH` env overrides.
