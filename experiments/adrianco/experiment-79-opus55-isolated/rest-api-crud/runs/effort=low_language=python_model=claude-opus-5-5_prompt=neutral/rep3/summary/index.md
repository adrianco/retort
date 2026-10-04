# Summary: rest-api-crud · effort=low language=python model=claude-opus-5-5 prompt=neutral · rep 3

- **Shape:** Python stdlib REST API — `http.server.ThreadingHTTPServer` + `sqlite3`, zero third-party dependencies.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 13 tests), README.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); one `books` SQLite table.
- **Notable:** Thread-safe store with a lock; unique-isbn `409` handling; `413` body-size guard; validation returns `422` rather than the `400` the task illustrates.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
