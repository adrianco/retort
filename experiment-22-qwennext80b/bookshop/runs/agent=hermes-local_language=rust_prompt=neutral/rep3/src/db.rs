use sqlx::{Pool, Sqlite};
use std::env;

pub async fn init_db_pool() -> Result<Pool<Sqlite>, sqlx::Error> {
    let database_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite://books.db".to_string());
    
    Pool::connect(&database_url).await
}
