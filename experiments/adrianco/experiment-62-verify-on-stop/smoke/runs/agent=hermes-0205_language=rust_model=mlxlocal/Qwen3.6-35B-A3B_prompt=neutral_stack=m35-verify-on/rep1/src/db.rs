use sqlx::sqlite::SqlitePool;
use sqlx::FromRow;

pub async fn get_pool() -> Result<SqlitePool, sqlx::Error> {
    let db_path = std::env::var("DATABASE_URL").unwrap_or_else(|_| {
        // Use file:// URI for proper SQLite path handling
        "file:/tmp/book-api.db".to_string()
    });
    let pool = SqlitePool::connect(&db_path).await?;
    Ok(pool)
}

#[derive(Debug, FromRow)]
pub struct BookRecord {
    pub id: String,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}
