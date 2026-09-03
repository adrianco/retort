# Summary: agent=hermes-0205 · language=go · model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · prompt=neutral · stack=dwq4 · rep 4

- **Shape:** Go `net/http` CRUD service over SQLite (`mattn/go-sqlite3`), single-file — no framework, no router library.
- **Structure:** 1 source module (`main.go`, 317 lines), 1 test file (`main_test.go`, 214 lines, 7 tests, 0 skipped), 2 direct dependencies.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 1 SQLite table, 0 CLI commands, 0 exported symbols.
- **Notable:** Manual path parsing (`TrimPrefix`/`Atoi`) instead of a mux with path params; tests call handler funcs directly rather than through the mux, so the `/books/` method-dispatch block in `main()` is never exercised; `?author=` uses a `LIKE %…%` substring match and has no test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
