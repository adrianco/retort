# Summary: rest-api-crud · rep 3

- **Shape:** Standard-library Python REST API — `wsgiref` WSGI app with SQLite storage, zero runtime dependencies.
- **Structure:** 1 source module (`app.py`), 1 test module (`test_app.py`), README + dev-deps manifest.
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter), 4 exported library symbols, 1 `books` table.
- **Notable:** No web framework at all — routing/validation/serialization are hand-rolled on `wsgiref`. Careful edge handling (bool-vs-int year, ISBN normalization, 1 MB body cap, SQL-injection-safe author filter, per-op connections for thread safety) and a real-socket end-to-end test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
