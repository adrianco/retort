# Summary: rest-api-crud effort=low language=typescript model=claude-opus-5-5 prompt=neutral · rep 3

- **Shape:** Zero-dependency TypeScript REST API on Node's `node:http`, backed by the built-in `node:sqlite`.
- **Structure:** 4 source modules, 1 test file (15 tests).
- **Interfaces:** 6 HTTP routes (`/health` + 5 `/books` CRUD), 1 exported `createApp()`, a `BookStore` class, and a `validateBook()` function.
- **Notable:** Uses only the Node standard library (no Express, no better-sqlite3). Adds beyond-spec touches: 1 MB body-size guard (413), 405 method-not-allowed with `Allow` header, `Location` header on create, and case-insensitive author filtering.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
