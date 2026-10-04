# Summary: effort=default language=python model=claude-fable-5-1 prompt=none · rep 3

- **Shape:** Zero-dependency Python REST API — `http.server` (ThreadingHTTPServer) + `sqlite3`, no web framework.
- **Structure:** 1 source module (app.py), 1 test file (test_app.py, 13 functions), README + dev requirements.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); one SQLite `books` table.
- **Notable:** Thread-safe store (single lock), explicit bool-vs-int year rejection, `HTTP/1.0` chosen to avoid keep-alive desync on rejected bodies, 411/413 guards — noticeably more careful than the task minimum.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
