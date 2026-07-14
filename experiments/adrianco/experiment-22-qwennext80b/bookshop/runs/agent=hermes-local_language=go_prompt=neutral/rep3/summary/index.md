# Summary: agent=hermes-local language=go prompt=neutral · rep 3

- **Shape:** Go `net/http` CRUD REST API using GORM over SQLite.
- **Structure:** 3 modules (main.go, server.go, server_test.go), 1 test file.
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter), 405 on bad methods.
- **Notable:** Standard-library router (Go 1.22 `{id}` pattern) but parses id manually via `TrimPrefix`+`Atoi` instead of `r.PathValue`. Validation goes beyond spec (year/isbn required, isbn unique → 409). Vestigial `binding:"required"` struct tags (gin-style) are unused with net/http.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
