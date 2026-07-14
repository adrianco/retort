# Summary: agent=hermes-local language=go prompt=neutral · rep 3

- **Shape:** Go `net/http` CRUD REST API over SQLite (`modernc.org/sqlite`, pure-Go), in-memory DB.
- **Structure:** 1 source module (`main.go`), 1 test file (`main_test.go`, 12 test functions).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 6 exported `BookStore` methods, 1 `books` table.
- **Notable:** Manual path-trimming router instead of a framework or Go 1.22 method patterns; `:memory:` store (no persistence); validation requires `year` in addition to the spec's title+author; UNIQUE-ISBN violations surfaced via error-string matching (`strings.Contains(err, "UNIQUE")`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
