# Summary: effort=xhigh language=python model=claude-haiku-5-5 prompt=neutral · rep 1

- **Shape:** Standard-library-only REST API (`http.server` + `sqlite3`), no runtime dependencies, layered into HTTP / validation / repository / models.
- **Structure:** 6 source modules, 3 test files (39 test functions incl. parametrisation).
- **Interfaces:** 6 primary HTTP routes (5 CRUD + health), 1 CLI entry point, 5 exported library symbols.
- **Notable:** Zero third-party runtime deps; clean layering with a dataclass domain model, centralised error mapping, a `Content-Length` guard (413), threaded server with lock-serialised shared connection, and ISBN/year normalisation beyond the spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
