//! Binary entry point: opens the database, builds the router, and serves it.

use std::sync::{Arc, Mutex};

use book_api::{app, open_db};

#[tokio::main]
async fn main() {
    // Configurable via environment; sensible defaults for local runs.
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());

    let conn = open_db(&db_path).expect("failed to open database");
    let db = Arc::new(Mutex::new(conn));

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind address");

    println!("Book API listening on http://{addr} (db: {db_path})");
    axum::serve(listener, app(db)).await.expect("server error");
}
