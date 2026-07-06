# Summary: language=go, model=opus-4.8, prompt=bdd · rep 1

- **Shape:** Go `net/http` (stdlib 1.22+ routing) CRUD REST API over a pure-Go embedded SQLite store (`modernc.org/sqlite`, no cgo).
- **Structure:** 4 source modules + 1 test file (11 test functions).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), one `books` SQLite table, small `Store`/`Server` library API.
- **Notable:** Clean layering (model / store / server / entrypoint); zero third-party web framework; BDD Given/When/Then test naming and comments per the prompt factor; `SetMaxOpenConns(1)` to keep in-memory DB stable.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
