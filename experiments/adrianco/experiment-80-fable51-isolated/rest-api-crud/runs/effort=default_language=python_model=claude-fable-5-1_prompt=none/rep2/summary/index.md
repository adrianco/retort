# Summary: rest-api-crud · rep 2

- **Shape:** Pure-stdlib Python WSGI REST API (`wsgiref`) with SQLite persistence — no third-party runtime dependency.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`), README + requirements.
- **Interfaces:** 6 HTTP routes (health + full CRUD) over one `books` table; `create_app()` factory exported.
- **Notable:** Zero-dependency approach (only `pytest` for tests); per-request SQLite connections; explicit type-checking in validation (rejects bool-as-int, non-string isbn); 405 with `Allow` header and JSON errors throughout.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
