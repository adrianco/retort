# Summary: agent=hermes-local language=go prompt=neutral · rep 1

- **Shape:** Go `net/http` CRUD REST API backed by SQLite (`mattn/go-sqlite3`), in-memory DB, no web framework.
- **Structure:** 4 source modules (main, handlers, database, models) + 1 test file (11 tests).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); no CLI; `BookStore`/`BookHandler` library types.
- **Notable:** Clean layered split (routing / handlers / store / models); manual path+method routing on a stdlib mux; `:memory:` SQLite so data is non-persistent; `handlers.go` carries two dead dispatcher methods (`HandleBooks`, `HandleBookByID`) unused by `main.go`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
