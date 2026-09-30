# Summary: effort=xhigh_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

- **Shape:** Go `net/http` (Go 1.22+ method+pattern routing) CRUD REST API backed by SQLite via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 3 source modules (`main`, `internal/books`, `internal/api`) + 2 test files.
- **Interfaces:** 6 HTTP routes (POST/GET/GET-by-id/PUT/DELETE `/books`, GET `/health`); one `books` SQLite table; `books.Store` + `api.Store` exported APIs.
- **Notable:** Standard-library-only routing with an explicit 405/404 JSON layer, request-body size cap, panic recovery + request-logging middleware, graceful shutdown, and SQLite URI-safe DSN handling — an unusually complete stdlib implementation for the task.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
