# Summary: language=go_model=sonnet-5_prompt=bdd · rep 1

- **Shape:** Go `net/http` (stdlib, method-aware ServeMux) CRUD API over SQLite via the pure-Go `modernc.org/sqlite` driver (no CGO).
- **Structure:** 4 source modules + 1 test file (11 BDD-style tests), ~582 LOC total.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), one `books` table, `Store` + `Book` library types.
- **Notable:** Clean layering (models / store / handlers / main); parameterized SQL; sentinel-error → HTTP-status mapping; env-var config. No third-party web framework. BDD prompt clearly followed — `Test_given_..._when_..._then_...` names with Given/When/Then comment sections.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
