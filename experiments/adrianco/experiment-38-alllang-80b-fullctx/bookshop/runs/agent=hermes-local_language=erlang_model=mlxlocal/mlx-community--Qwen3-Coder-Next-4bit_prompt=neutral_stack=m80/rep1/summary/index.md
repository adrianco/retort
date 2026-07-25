# Architecture Summary — Erlang Book API

*Generated inline (the `run-summary` skill's role) during evaluation.*

## Overview

An OTP application (`book_api`) implementing a REST book-collection service on
Cowboy 2.10 with a SQLite backend (`sqlite3` NIF library) and JSON via `jiffy`.

## Modules

| Module | Role |
|--------|------|
| `book_api_app` | OTP application callback — starts the supervisor. |
| `book_api_sup` | `one_for_one` supervisor; children: `book_api_db` (gen_server) then `book_api_rest` (HTTP listener). |
| `book_api_rest` | Compiles the Cowboy dispatch (`/health`, `/books`, `/books/:id`) and starts the clear (HTTP) listener on port 8080. |
| `book_api_handler` | Cowboy handler for `/books` and `/books/:id` — dispatches by method, reads/decodes body, calls `book_api_db`, replies JSON. |
| `book_api_health` | Cowboy handler for `/health` — calls `book_api_db:health_check/0`, replies 200/503. |
| `book_api_db` | `gen_server` wrapping SQLite. Owns schema init, CRUD, validation, health. Opens/closes a fresh `sqlite3` connection per call against file `books.db`. |

## Request flow

`cowboy listener → dispatch → book_api_handler:init/2 → handle_*_request/N →
book_api_db:<op> (gen_server:call) → sqlite3 → JSON reply`.

`/health` bypasses `book_api_handler` and goes straight to `book_api_health`.

## Data model

Single `books` table: `id` (autoincrement PK), `title` NOT NULL, `author` NOT
NULL, `year` INTEGER, `isbn` TEXT UNIQUE. Persisted to on-disk `books.db`.

## Notable architectural observations

- **Two-layer split is clean at the db level but the HTTP layer is unverified.**
  Every test calls `book_api_db` directly with atom-keyed maps; no test issues a
  real HTTP request, so `book_api_handler` / `book_api_rest` / `book_api_health`
  are entirely untested.
- **The HTTP handler relies on Cowboy/jiffy APIs that do not exist or are
  misused** (see `findings.jsonl`): `cowboy_req:match_params/1`,
  `cowboy_req:query_param/2`, and `jiffy:decode/1` without `return_maps`.
- Persistent shared `books.db` file across gen_server restarts makes the
  order-dependent tests flaky (schema init is skipped when the file already
  exists).
