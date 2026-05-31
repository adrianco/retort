use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use sqlx::Executor;

pub type Db = SqlitePool;

pub async fn init(url: &str) -> Result<Db, sqlx::Error> {
    // For file-backed SQLite, ensure the file exists by appending ?mode=rwc
    let connect_url = if url.starts_with("sqlite::memory:") || url.contains("mode=") {
        url.to_string()
    } else {
        format!("{}?mode=rwc", url)
    };

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&connect_url)
        .await?;

    pool.execute(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );
        "#,
    )
    .await?;

    Ok(pool)
}
