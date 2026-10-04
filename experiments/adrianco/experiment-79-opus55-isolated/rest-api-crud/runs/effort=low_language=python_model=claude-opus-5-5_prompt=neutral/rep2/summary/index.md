# Summary: rest-api-crud (effort=low, python, opus-5-5, neutral) · rep 2

- **Shape:** Standard-library-only REST API — `http.server.ThreadingHTTPServer` + `sqlite3`, zero runtime dependencies.
- **Structure:** 1 source module (app.py), 1 test module (test_app.py), README.md.
- **Interfaces:** 6 HTTP routes (health + full CRUD), 1 SQLite table, 3 exported library symbols.
- **Notable:** No web framework at all — hand-rolled dispatcher with correct 400/404/405/413/500 handling, per-operation SQLite connections for thread safety, and a `bool`-excluding year check. Tests drive the real server over a socket.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
