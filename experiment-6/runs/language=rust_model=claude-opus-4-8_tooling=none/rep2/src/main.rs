//! Binary entry point: starts the HTTP server.

use book_api::{app, file_db};

#[tokio::main]
async fn main() {
    // Database file path (override with DATABASE_PATH).
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let db = file_db(&db_path);

    // Bind address (override with BIND_ADDR).
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("bind address");

    println!("Book API listening on http://{addr} (db: {db_path})");
    axum::serve(listener, app(db)).await.expect("server error");
}
