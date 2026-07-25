# Summary: erlang · claude-opus-5 · neutral · rep 1

- **Shape:** Erlang/OTP REST API — Cowboy HTTP handlers over an Mnesia `disc_copies` store, with a pure validation module and shared JSON plumbing.
- **Structure:** 11 source modules + 1 record header + app/config files; 4 test modules (1 helper) with 20 unit tests plus store, durability and live-HTTP integration generators.
- **Interfaces:** 6 CRUD/health HTTP routes (plus 405 and catch-all 404 handling); no CLI; `book` and `book_store` exported as reusable APIs.
- **Notable:** Clean separation of pure domain logic (`book`) from persistence (`book_store`) and transport (`book_api_http` + per-route handlers). Validation goes beyond the spec (length caps, year range, structural ISBN check); uses Mnesia instead of SQLite; every error shares one JSON envelope; HEAD supported and unmatched routes get JSON 404. Config via env vars with app-env fallback.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
