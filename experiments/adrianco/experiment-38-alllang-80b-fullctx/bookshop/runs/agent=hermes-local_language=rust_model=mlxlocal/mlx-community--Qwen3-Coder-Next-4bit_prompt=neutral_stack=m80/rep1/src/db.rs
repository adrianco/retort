use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};

pub type DbPool = Pool<Sqlite>;

#[derive(Clone)]
pub struct AppState {
    pub pool: DbPool,
}

pub async fn init_db() -> Result<DbPool, sqlx::Error> {
    // Use in-memory SQLite for testing, file-based for production
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite://books.db?mode=rwc".to_string());

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await?;

    // Create the books table if it doesn't exist
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL UNIQUE
        )
        "#,
    )
    .execute(&pool)
    .await?;

    Ok(pool)
}
