use sqlx::SqlitePool;

pub async fn ensure_schema(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL
        )
        "#
    )
    .execute(pool)
    .await?;

    Ok(())
}
