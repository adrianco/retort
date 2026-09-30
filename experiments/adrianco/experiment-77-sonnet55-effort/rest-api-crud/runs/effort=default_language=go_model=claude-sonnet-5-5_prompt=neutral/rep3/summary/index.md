# Summary: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

- **Shape:** Go `net/http` (1.22+ method-pattern routing) CRUD service with SQLite persistence via pure-Go `modernc.org/sqlite`.
- **Structure:** 2 source modules (`main.go`, `store.go`) + 1 test file (`main_test.go`), plus README.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`); store exposes `NewStore`, `Create`, `Get`, `List`, `Update`, `Delete`.
- **Notable:** Clean separation of HTTP layer from persistence; extras beyond spec — `MaxBytesReader` body cap, `Location` header on create, negative-year validation, env-configurable `ADDR`/`DB_PATH`, `:memory:` DB in tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
