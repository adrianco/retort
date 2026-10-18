# Summary: agent=codex effort=low language=erlang model=gpt-6-luna prompt=neutral · rep 1

- **Shape:** Erlang/OTP + Cowboy REST API with SQLite persistence (via spawned `sqlite3 -json` port)
- **Structure:** 4 source modules (app, handler, store, app.src), 1 test file (3 EUnit tests)
- **Interfaces:** 6 HTTP routes (health + full CRUD on /books), 5 exported store functions
- **Notable:** Unusual persistence strategy — instead of an Erlang SQLite NIF/driver, it shells out to
  the `sqlite3` CLI once per query and parses its `-json` output. SQL is built by string interpolation
  with manual quote escaping (not parameterized). Compiles with `warnings_as_errors`; all tests pass.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
