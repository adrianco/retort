# Summary: effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

- **Shape:** Go stdlib `net/http` CRUD REST API backed by an embedded SQLite database (pure-Go `modernc.org/sqlite`, no cgo).
- **Structure:** 4 source modules (`main.go`, `handlers.go`, `store.go` + 1 test file `handlers_test.go`), 1 test file.
- **Interfaces:** 6 HTTP routes (`/health`, `POST/GET /books`, `GET/PUT/DELETE /books/{id}`); persistence via a single `books` table.
- **Notable:** Uses the Go 1.22 method+pattern routing (`GET /books/{id}`) with no third-party web framework; body decoding hardens against oversized payloads and unknown fields; single-connection pool to keep SQLite consistent.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
