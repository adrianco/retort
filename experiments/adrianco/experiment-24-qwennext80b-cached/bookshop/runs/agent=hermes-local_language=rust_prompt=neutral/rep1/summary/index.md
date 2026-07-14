# Summary: agent=hermes-local language=rust prompt=neutral · rep 1

- **Shape:** Rust actix-web REST CRUD API over SQLite (rusqlite bundled), split into a `book_api` lib + thin binary.
- **Structure:** 2 Rust source files (lib.rs, main.rs) + 1 SQL migration; tests live inline in `lib.rs` (3 `#[test]` fns).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 6 exported handler functions, one `books` table.
- **Notable:** Migration file is dead (schema created inline); a full `#[actix_web::main] fn main` is duplicated into `lib.rs` as dead code; the 3 tests are tautological (assert on locally-constructed values, exercise no handler/DB); `update_book`'s numbered-placeholder scheme breaks partial PUTs.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
