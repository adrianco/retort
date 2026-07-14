use r2d2_sqlite::SqliteConnectionManager;

pub type Pool = r2d2::Pool<SqliteConnectionManager>;

/// Builds a connection pool backed by the sqlite file at `path` (or an
/// in-memory database when `path` is `:memory:`) and ensures the schema
/// exists.
pub fn init_pool(path: &str) -> Pool {
    let manager = if path == ":memory:" {
        SqliteConnectionManager::memory()
    } else {
        SqliteConnectionManager::file(path)
    };
    let pool = r2d2::Pool::builder()
        .max_size(if path == ":memory:" { 1 } else { 8 })
        .build(manager)
        .expect("failed to build sqlite connection pool");

    let conn = pool.get().expect("failed to get initial connection");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )",
        [],
    )
    .expect("failed to create books table");

    pool
}
