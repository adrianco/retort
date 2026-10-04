# Summary: effort=low_language=c_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** Framework-free C11 REST API — hand-rolled POSIX-socket HTTP/1.1 server in front of SQLite, with a hand-written JSON parser/serializer.
- **Structure:** 3 source modules (`app.c`, `app.h`, `server.c`) + 2 test files (`test_app.c`, `test_http.sh`).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); 2 exported functions (`app_open_db`, `app_handle`).
- **Notable:** No third-party dependency beyond `libsqlite3` — the JSON parsing (incl. `\u` surrogate pairs), HTTP framing, and routing are all implemented by hand; SQL uses bound parameters throughout; clean separation of the app layer (`app_handle`) from transport (`server.c`) lets tests exercise handlers directly against an in-memory DB.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
