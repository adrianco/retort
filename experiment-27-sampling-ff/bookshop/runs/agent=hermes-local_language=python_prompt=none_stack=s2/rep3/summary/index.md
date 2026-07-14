# Summary: agent=hermes-local language=python prompt=none stack=s2 · rep 3

- **Shape:** Flask REST API with raw `sqlite3` storage (application-factory pattern).
- **Structure:** 1 source module + 1 test module, 24 test functions.
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`), 1 exported factory `create_app()`.
- **Notable:** Clean factory design with a `':memory:'` shared-connection path for isolated tests; substring author filter via `LIKE`; no pagination and no ISBN/year format validation.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
