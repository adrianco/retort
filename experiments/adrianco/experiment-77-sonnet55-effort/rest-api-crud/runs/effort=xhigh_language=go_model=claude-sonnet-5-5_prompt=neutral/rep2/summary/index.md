# Summary: effort=xhigh_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

- **Shape:** Go `net/http` REST CRUD service with an embedded SQLite store (pure-Go `modernc.org/sqlite` driver, no cgo).
- **Structure:** 5 source modules (main + store + 3 api files) across 2 packages, 2 test files.
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD, with `?author=` filter), `store.Store` repository API behind a `BookStore` interface.
- **Notable:** Production-grade for the task — graceful shutdown, request-logging + panic-recovery middleware, 1 MiB body cap, strict JSON decoding (trailing-data + type errors), per-field validation, `Location` header on create, `405`+`Allow` and `HEAD`-as-`GET` handling, WAL mode. Store injected via interface, enabling failure-injection tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
