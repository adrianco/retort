# Architecture Summary — book-api (Rust / Actix Web)

Single-crate Actix Web service, entire implementation in `src/main.rs` (230 lines).

## Modules / structure
- **Data models** (`main.rs:6-34`): `Book`, `BookCreate`, `BookUpdate`, `HealthResponse` — serde `Serialize`/`Deserialize` structs.
- **Storage** (`main.rs:36-40`): process-global `lazy_static` state — `BOOKS: Mutex<Vec<Book>>` and `NEXT_ID: Mutex<u32>`. In-memory only; no database.
- **Handlers** (`main.rs:42-144`): async fns `health`, `create_book`, `get_books`, `get_book`, `update_book`, `delete_book`.
- **Tests** (`main.rs:146-212`): 3 `#[actix_web::test]` cases (health, create+get, list).
- **Bootstrap** (`main.rs:214-231`): `HttpServer` binds `127.0.0.1:8080`, wires routes, `Logger` middleware.

## Request flow
HTTP → Actix router → handler → lock the global `Mutex<Vec<Book>>` → mutate/read Vec → serialize `HttpResponse::*().json(...)`.

## Notable design points
- IDs are `format!("book-{}", NEXT_ID)`, monotonic counter.
- `?author=` filter uses substring `.contains()` (not exact match).
- Validation (non-empty title/author) is enforced on create only.
- No persistence layer — all data is lost on restart, and is global rather than injected app state.
