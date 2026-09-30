# Summary: rest-api-crud (effort=xhigh, python, claude-sonnet-5-5, neutral) · rep 3

- **Shape:** Stdlib-only WSGI REST API (`wsgiref` + `sqlite3`), no third-party framework or dependencies.
- **Structure:** 5 source modules, 3 test files (+ conftest); ~470 source lines, ~490 test lines.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), one CLI entry (`python -m bookapi`), a small library API (`create_app`, `BookApp`, `BookStore`, `validate_book`), one `books` table.
- **Notable:** Zero-dependency design leaning on the standard library; thread-safe single-connection store with a lock; a custom Unicode `CASEFOLD` collation for author filtering; extensive edge-case coverage (42 tests spanning oversized bodies, bad Content-Length, SQL-injection-safe filtering, 64-bit id range guards, concurrent-thread access, and a full HTTP-socket lifecycle test).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
