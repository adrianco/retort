use book_api::{create_router, init_db};
use sqlx::SqlitePool;

#[tokio::main]
async fn main() {
    let db_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite://books.db".to_string());

    let pool = SqlitePool::connect(&db_url)
        .await
        .expect("Failed to connect to database");

    init_db(&pool).await;

    let app = create_router(pool);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("Failed to bind to port 3000");

    println!("Server running on http://0.0.0.0:3000");
    axum::serve(listener, app).await.expect("Server failed");
}
