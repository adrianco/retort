# Summary: effort=low language=erlang model=claude-opus-5-5 prompt=neutral · rep 2

- **Shape:** Erlang/OTP REST API on Cowboy with SQLite persistence via esqlite3, JSON via OTP's built-in `json` module.
- **Structure:** 4 source modules (app, supervisor, DB gen_server, HTTP handler) + 1 app.src, 1 test file.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), one `books` table.
- **Notable:** Idiomatic OTP layout — supervised gen_server serialising all DB access; full validation with per-field 422 details, `Location` header on create, 405/413 handling, and a macOS `-bundle` LDFLAGS workaround in `rebar.config.script`. Tests boot the app against an in-memory SQLite DB and exercise every endpoint over real HTTP.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
