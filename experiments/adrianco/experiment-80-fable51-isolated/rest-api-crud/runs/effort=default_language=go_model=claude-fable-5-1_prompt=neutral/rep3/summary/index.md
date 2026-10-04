# Summary: effort=default language=go model=claude-fable-5-1 prompt=neutral · rep 3

- **Shape:** Go `net/http` CRUD REST API backed by SQLite via the pure-Go `modernc.org/sqlite` driver (no cgo).
- **Structure:** 3 source modules (main/handlers/store) + 1 test file (6 test functions, ~28 subtests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`); ~11 exported functions/types in package `main`.
- **Notable:** Idiomatic Go 1.22 method-pattern routing; body-size limit + `DisallowUnknownFields` hardening; single-connection pool to keep `:memory:` and writes consistent; file-persistence test reopens the DB. Validation errors use `422` rather than the `400` the spec example suggests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
