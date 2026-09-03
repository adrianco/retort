# Summary: agent=hermes-0205 language=go model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-8bit prompt=neutral stack=q8 · rep 4

- **Shape:** Go `net/http` CRUD service over SQLite (`mattn/go-sqlite3`), single `package main` file, no framework or router library.
- **Structure:** 1 source module (`main.go`, 280 lines), 1 test file (`main_test.go`, 321 lines, 9 tests + `TestMain`), 1 shell smoke script, 1 dependency.
- **Interfaces:** 7 HTTP routes (health + 5 CRUD + author filter), 1 SQLite table, 0 CLI commands, 0 exported library symbols.
- **Notable:** Hand-rolled method dispatch and path-id parsing instead of a router; the `?author=` filter is a SQL `LIKE '%…%'` substring match; tests exercise handlers directly via `httptest` against the same `./books.db` the server uses.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
