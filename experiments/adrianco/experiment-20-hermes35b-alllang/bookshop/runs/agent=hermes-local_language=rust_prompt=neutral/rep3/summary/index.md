# Summary: agent=hermes-local language=rust prompt=neutral · rep 3

- **Shape:** Rust actix-web REST CRUD API backed by SQLite (rusqlite, bundled).
- **Structure:** 1 module (single `src/main.rs`), 10 tests in an in-file `#[cfg(test)]` module.
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), 1 SQLite table, `Db` data-access layer.
- **Notable:** Fully self-contained single file; shared connection via `Arc<Mutex<Connection>>` serializes DB access; two handlers use `.unwrap()` on a DB lookup that would panic rather than return 500.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
