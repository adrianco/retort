use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use sqlx::Sqlite;
use std::str::FromStr;

pub type DbPool = SqlitePool;

pub async fn init_pool(database_url: &str) -> Result<DbPool, sqlx::Error> {
    let opts = sqlx::sqlite::SqliteConnectOptions::from_str(database_url)?
        .create_if_missing(true);

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect_with(opts)
        .await?;

    init_schema(&pool).await?;
    Ok(pool)
}

pub async fn init_schema(pool: &sqlx::Pool<Sqlite>) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        "#,
    )
    .execute(pool)
    .await?;
    Ok(())
}
