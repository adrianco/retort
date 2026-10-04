# Summary: effort=low_language=rust_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Rust axum 0.8 REST API with SQLite persistence (rusqlite, bundled).
- **Structure:** 2 source modules (`lib.rs`, `main.rs`) + 1 test file (9 tests).
- **Interfaces:** 6 HTTP routes (+ health, + fallback) / 0 CLI commands / 4 exported symbols.
- **Notable:** Clean separation of a testable `app(state)` router from the binary; typed
  `ApiError` enum with `IntoResponse`; extractor-rejection handling (`JsonRejection`,
  `PathRejection`) turns malformed bodies and non-integer ids into 400s; graceful shutdown
  on ctrl-c. Synchronous SQLite under a global `Mutex` inside async handlers.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
