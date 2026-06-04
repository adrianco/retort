use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;

pub type DbPool = Pool<SqliteConnectionManager>;

/// Build a connection pool for the database at `path` (use ":memory:" for an
/// in-memory database) and ensure the schema exists.
pub fn init_pool(path: &str) -> DbPool {
    let is_memory = path == ":memory:";
    let manager = if is_memory {
        SqliteConnectionManager::memory()
    } else {
        SqliteConnectionManager::file(path)
    };
    let mut builder = Pool::builder();
    if is_memory {
        // Each in-memory connection is its own database, so cap the pool at a
        // single connection to keep all requests pointed at the same data.
        builder = builder.max_size(1);
    }
    let pool = builder
        .build(manager)
        .expect("failed to create connection pool");

    let conn = pool.get().expect("failed to get connection");
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        );",
    )
    .expect("failed to initialize schema");

    pool
}
