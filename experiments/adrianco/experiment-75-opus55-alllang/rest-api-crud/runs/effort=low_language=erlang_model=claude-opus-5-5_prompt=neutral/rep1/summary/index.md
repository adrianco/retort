# Architecture Summary: Books REST API (Erlang / OTP)

A zero-dependency OTP application. 4 source modules + 1 CT suite, 228 LOC total.

## Modules

| Module | Role | Key exports |
|--------|------|-------------|
| `books_app` | OTP `application` behaviour. Reads `port`/`db_file` env, opens the store, starts `inets` httpd with `books_http` as the request module, and holds the httpd pid in `persistent_term`. | `start/2`, `stop/1` |
| `books_http` | inets httpd callback. Parses method + path segments + query, routes to the store, and encodes JSON replies with status codes. Owns request validation. | `do/1`, `validate/1` |
| `books_store` | Persistence over DETS (embedded on-disk store, used in place of SQLite). Auto-increment id via `dets:update_counter`, set table keyed by integer id, `'$counter'` sentinel row for the id sequence. | `open/1`, `close/0`, `create/1`, `list/1`, `get/1`, `update/2`, `delete/1` |
| `books.app.src` | App resource file. `applications: [kernel, stdlib, inets]`, env defaults `port=8080`, `db_file="books.dets"`. | — |

## Request flow

`httpd` → `books_http:do/1` → split URI into `{Path, Query}` → segment list →
`route/4`:
- `GET /health` → `{200, #{status => ok}}`
- `GET /books[?author=]` → `books_store:list/1` (optional exact-author filter)
- `POST /books` → `with_valid` → `books_store:create/1` → 201
- `GET|PUT|DELETE /books/{id}` → `book_route/3` → store get/update/delete → 200/204/404
- validation failure → 400 with `details`; bad JSON → 400; non-integer id → 404; unmatched → 404; any exception → 500

## Notes

- Persistence is DETS, an embedded disk store bundled with OTP — the language-equivalent of SQLite the task allows (no native driver needed).
- Validation lives in `books_http:validate/1`: `title`/`author` are required non-empty binaries; `year` (if present) must be integer, `isbn` (if present) a string; `null` is tolerated for optionals; unknown keys are stripped via `maps:with`.
