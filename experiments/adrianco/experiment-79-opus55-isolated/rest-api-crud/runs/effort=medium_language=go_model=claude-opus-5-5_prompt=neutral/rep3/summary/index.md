# Summary: effort=medium_language=go_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Go `net/http` (1.22+ method-pattern mux) CRUD REST API backed by SQLite via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 3 source modules (main/handlers/store) + 1 test file, 654 lines of Go total.
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), one `books` table, small exported store/handler API.
- **Notable:** No third-party web framework — stdlib routing only; CGO-free SQLite driver; graceful shutdown, context propagation, 1 MiB body cap, strict JSON decoding, and case-insensitive author filter go beyond the minimum spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
