# Summary: agent=hermes-0205 · go · Qwen3-Coder-30B-A3B-Instruct-8bit (q8, neutral) · rep 5

- **Shape:** Go stdlib `net/http` CRUD service over SQLite via `database/sql` + `mattn/go-sqlite3`, single file.
- **Structure:** 1 source module (319 lines) + 1 test file (193 lines, 6 tests); 2 direct dependencies.
- **Interfaces:** 6 HTTP routes, 0 CLI commands, 0 exported symbols, 1 table.
- **Notable:** no third-party router or web framework — `ServeMux` with manual method dispatch and `TrimPrefix` id parsing; tests exercise handlers directly against the real on-disk `books.db`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
