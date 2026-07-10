mod db;
mod models;
mod routes;

use std::env;

#[tokio::main]
async fn main() {
    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string());

    let pool = db::create_pool(&database_url)
        .await
        .expect("Failed to create database pool");

    db::init_db(&pool)
        .await
        .expect("Failed to initialize database");

    let app = routes::create_router(pool);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("Failed to bind to port 3000");

    println!("Book API server running on http://0.0.0.0:3000");

    axum::serve(listener, app)
        .await
        .expect("Server failed");
}
